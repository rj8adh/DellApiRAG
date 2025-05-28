import sys
import time # Import the time module
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from embeddingsMain import get_embed_function
from langchain.schema.document import Document
from pprint import pprint
import argparse
import json
import re
import os

# --- MODIFICATION: Import the new query reframer ---
from reframeQuery import reframe_query_with_history

# --- Constants ---
CHROMADATAPATH = 'chromaDb'
DTIAS_COLLECTION_NAME = "DTIAS"
CLOUDIFY_COLLECTION_NAME = "Cloudify"
RAG_FORMATTED_DATA_PATH = "ScrapingStuff/storedData/RagFormattedData.json"

PROMPT = """
You are an AI Documentation Chatbot. Your sole purpose is to provide answers based *exclusively* on the API documentation context provided below.
You must not use any external knowledge or make assumptions beyond what is written in the context.
It is crucial that you *do not* mention the process of information retrieval, the context itself, or that you are basing your answer on provided documents. Act as if you inherently know this information from the documentation.
If the answer to the question cannot be found within the provided context, you *must* state: 'The information to answer this question is not available in the provided documentation.' Do not attempt to infer, guess, or provide related information not directly supported by the context.

Provided API Documentation Context:
{context}

---

Based *only* on the Provided API Documentation Context above, answer the following user question:
User Question: {question}
Answer:
"""

# --- Global Initialization of Expensive Resources ---
print("\nCONTEXT_MODEL.PY: Initializing global resources...")
start_time_global_init = time.time()

# 1. LLM Model
try:
    MODEL = OllamaLLM(model="deepseek-coder:6.7b-instruct", temperature=.3)
    print("✅ Global LLM (MODEL) initialized.")
except Exception as e:
    MODEL = None
    print(f"❌ Failed to initialize global LLM (MODEL): {e}")

# 2. Embedding Function
try:
    EMBEDDING_FUNCTION = get_embed_function()
    print("✅ Global EMBEDDING_FUNCTION initialized.")
except Exception as e:
    EMBEDDING_FUNCTION = None
    print(f"❌ Failed to initialize global EMBEDDING_FUNCTION: {e}")

# 3. ChromaDB Connections
DB_DTIAS = None
DB_CLOUDIFY = None

if EMBEDDING_FUNCTION and os.path.exists(CHROMADATAPATH):
    try:
        DB_DTIAS = Chroma(
            persist_directory=CHROMADATAPATH,
            embedding_function=EMBEDDING_FUNCTION,
            collection_name=DTIAS_COLLECTION_NAME
        )
        print(f"✅ Global Chroma DB connection (DB_DTIAS) established to {CHROMADATAPATH} for collection '{DTIAS_COLLECTION_NAME}'.")
    except Exception as e:
        DB_DTIAS = None
        print(f"❌ Failed to establish global Chroma DB connection (DB_DTIAS) for collection '{DTIAS_COLLECTION_NAME}': {e}")

    try:
        DB_CLOUDIFY = Chroma(
            persist_directory=CHROMADATAPATH,
            embedding_function=EMBEDDING_FUNCTION,
            collection_name=CLOUDIFY_COLLECTION_NAME
        )
        print(f"✅ Global Chroma DB connection (DB_CLOUDIFY) established to {CHROMADATAPATH} for collection '{CLOUDIFY_COLLECTION_NAME}'.")
    except Exception as e:
        DB_CLOUDIFY = None
        print(f"⚠️ Failed to establish global Chroma DB connection (DB_CLOUDIFY) for collection '{CLOUDIFY_COLLECTION_NAME}': {e}. This might be expected if the collection doesn't exist yet.")

elif not os.path.exists(CHROMADATAPATH):
    print(f"⚠️ Global Chroma DB path not found at {CHROMADATAPATH}. DB connections not initialized.")
elif not EMBEDDING_FUNCTION:
    print(f"⚠️ Embedding function not available. DB connections not initialized.")


# 4. Formatted RAG Data (optional, if used frequently)
ALL_RAG_DATA = None
if os.path.exists(RAG_FORMATTED_DATA_PATH):
    try:
        with open(RAG_FORMATTED_DATA_PATH, 'r') as f:
            ALL_RAG_DATA = json.load(f)
        print(f"✅ Global RAG Formatted Data (ALL_RAG_DATA) loaded from {RAG_FORMATTED_DATA_PATH}.")
    except Exception as e:
        ALL_RAG_DATA = None
        print(f"❌ Failed to load global RAG Formatted Data (ALL_RAG_DATA): {e}")
else:
    print(f"⚠️ Global RAG Formatted Data path not found at {RAG_FORMATTED_DATA_PATH}. Not loaded.")

end_time_global_init = time.time()
print(f"CONTEXT_MODEL.PY: Global resource initialization complete in {end_time_global_init - start_time_global_init:.4f} seconds.")
# --- End of Global Initialization ---


def parse_chunk_id(chunk_id: str) -> tuple[str | None, int | None]:
    match = re.match(r"^(.*):(\d+)$", chunk_id)
    if match:
        source = match.group(1)
        index = int(match.group(2))
        return source, index
    return None, None

def read_entire_cloudify_file(file_path: str) -> str:
    """Read the entire content of a Cloudify documentation file."""
    file_path.replace(r"\\", "/")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error reading Cloudify file {file_path}: {e}")
        return f"[Error reading file: {file_path}]"

def get_contextual_chunks(
    db_dtias_conn: Chroma | None,
    db_cloudify_conn: Chroma | None,
    # This parameter is the text used for searching the DB.
    text_for_embedding_search: str,
    include_cloudify: bool,
    k: int = 4,
    window: int = 1
) -> tuple[list[Document], list[str], list[str]]:
    print("\nGET_CONTEXTUAL_CHUNKS: Starting...")
    start_time_get_contextual = time.time()

    if not db_dtias_conn:
        print("❌ GET_CONTEXTUAL_CHUNKS: DTIAS DB connection (db_dtias_conn) is not available.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (DTIAS DB not available) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []
    
    if include_cloudify and not db_cloudify_conn:
        print("⚠️ GET_CONTEXTUAL_CHUNKS: Cloudify inclusion requested, but Cloudify DB connection (db_cloudify_conn) is not available. Proceeding with DTIAS only.")
        include_cloudify = False

    print(f"🔎 GET_CONTEXTUAL_CHUNKS: Searching with embedding text: '{text_for_embedding_search}'")
    start_time_search = time.time()
    
    dtias_results = []
    cloudify_results = []

    # Query DTIAS collection - get top 2 results
    if db_dtias_conn:
        try:
            dtias_search = db_dtias_conn.similarity_search_with_score(text_for_embedding_search, k=2)
            for doc, score in dtias_search:
                doc.metadata['_collection_source'] = 'dtias'
            dtias_results = dtias_search
            print(f"GET_CONTEXTUAL_CHUNKS: Found {len(dtias_results)} results from DTIAS (top 2).")
        except Exception as e:
            print(f"❌ GET_CONTEXTUAL_CHUNKS: Error searching DTIAS collection: {e}")

    # Query Cloudify collection - get top 2 results
    if include_cloudify and db_cloudify_conn:
        try:
            cloudify_search = db_cloudify_conn.similarity_search_with_score(text_for_embedding_search, k=2)
            for doc, score in cloudify_search:
                doc.metadata['_collection_source'] = 'cloudify'
            cloudify_results = cloudify_search
            print(f"GET_CONTEXTUAL_CHUNKS: Found {len(cloudify_results)} results from Cloudify (top 2).")
        except Exception as e:
            print(f"❌ GET_CONTEXTUAL_CHUNKS: Error searching Cloudify collection: {e}")

    end_time_search = time.time()
    print(f"GET_CONTEXTUAL_CHUNKS: Similarity search completed in {end_time_search - start_time_search:.4f} seconds.")

    if not dtias_results and not cloudify_results:
        print("❌ GET_CONTEXTUAL_CHUNKS: NO RESULTS FOUND FOR THE QUERY from any active collection.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (no results) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    print(f"GET_CONTEXTUAL_CHUNKS: Processing {len(dtias_results)} DTIAS and {len(cloudify_results)} Cloudify results...")
    start_time_process = time.time()

    retrieved_docs_combined = []
    all_sources = []

    # Process DTIAS results - use context window as before
    if dtias_results:
        all_ids_to_fetch_dtias = set()
        for doc, score in dtias_results:
            doc_id = doc.metadata.get("id")
            if not doc_id:
                continue
            
            source_file, index = parse_chunk_id(doc_id)
            if source_file is None or index is None:
                continue

            all_ids_to_fetch_dtias.add(doc_id)
            
            # Add context window
            for offset in range(-window, window + 1):
                if offset == 0:
                    continue
                neighbor_index = index + offset
                if neighbor_index >= 0:
                    neighbor_id = f"{source_file}:{neighbor_index}"
                    all_ids_to_fetch_dtias.add(neighbor_id)

        # Fetch DTIAS chunks
        if all_ids_to_fetch_dtias:
            list_ids_dtias = list(all_ids_to_fetch_dtias)
            try:
                retrieved_data_dtias = db_dtias_conn.get(ids=list_ids_dtias, include=["documents", "metadatas"])
                if retrieved_data_dtias and retrieved_data_dtias.get('ids'):
                    for id_val, doc_content, meta in zip(retrieved_data_dtias.get('ids', []), retrieved_data_dtias.get('documents', []), retrieved_data_dtias.get('metadatas', [])):
                        if id_val and doc_content is not None and meta is not None:
                            meta['_collection_source'] = 'dtias'
                            retrieved_docs_combined.append(Document(page_content=doc_content, metadata=meta))
                            source = meta.get('source')
                            if source and source not in all_sources:
                                all_sources.append(source)
            except Exception as e:
                print(f"❌ GET_CONTEXTUAL_CHUNKS: Error retrieving DTIAS chunks: {e}")

    # Process Cloudify results - read entire files
    if cloudify_results:
        processed_cloudify_files = set()
        for doc, score in cloudify_results:
            doc_id = doc.metadata.get("id")
            if not doc_id:
                continue
            
            # Extract file path by removing chunk number
            file_path = doc_id.split("#")[0]
            
            if file_path in processed_cloudify_files:
                continue
            
            processed_cloudify_files.add(file_path)
            
            full_content = read_entire_cloudify_file(file_path)
            
            full_doc = Document(
                page_content=full_content,
                metadata={
                    'source': file_path,
                    'id': file_path,
                    '_collection_source': 'cloudify',
                    'is_full_file': True
                }
            )
            retrieved_docs_combined.append(full_doc)
            
            if file_path not in all_sources:
                all_sources.append(file_path)

    # Sort documents
    def sort_key(doc):
        collection_pref = 0 if doc.metadata.get("_collection_source") == "dtias" else 1
        if doc.metadata.get("is_full_file"):
            return (collection_pref, doc.metadata.get("source", ""), 0)
        else:
            doc_id = doc.metadata.get("id", "")
            source, index = parse_chunk_id(doc_id)
            source_val = source if source is not None else ""
            index_val = index if index is not None else -1
            return (collection_pref, source_val, index_val)

    retrieved_docs_combined.sort(key=sort_key)
    
    context_docs = retrieved_docs_combined
    sorted_retrieved_ids = [doc.metadata.get("id", "N/A") for doc in context_docs]

    end_time_process = time.time()
    print(f"✅ GET_CONTEXTUAL_CHUNKS: Processed and sorted {len(context_docs)} documents in {end_time_process - start_time_process:.4f} seconds.")
    print(f"   - DTIAS docs: {len([d for d in context_docs if d.metadata.get('_collection_source') == 'dtias'])}")
    print(f"   - Cloudify docs: {len([d for d in context_docs if d.metadata.get('_collection_source') == 'cloudify'])}")

    end_time_get_contextual = time.time()
    print(f"GET_CONTEXTUAL_CHUNKS: Finished total execution in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
    return context_docs, sorted_retrieved_ids, all_sources


def single_query(query_text: str, use_cloudify_docs: bool = True, use_formatted_data: bool = False, k_val:int = 4, text_to_embed: str = ""):
    # This check ensures that if the reframer fails and text_to_embed is empty,
    # we fall back to using the main query_text for the embedding search.
    if not text_to_embed:
        text_to_embed = query_text
        
    print(f"\nSINGLE_QUERY: Starting for query: '{query_text}' | use_cloudify_docs: {use_cloudify_docs} | use_formatted_data: {use_formatted_data}")
    start_time_single_query = time.time()

    # --- Check if global resources are available ---
    if not MODEL:
        print("❌ SINGLE_QUERY: Global LLM (MODEL) not available.")
        def error_gen(): yield "Error: The AI model is not available."
        return error_gen(), []


    if not EMBEDDING_FUNCTION:
        print("❌ SINGLE_QUERY: Global EMBEDDING_FUNCTION not available.")
        def error_gen(): yield "Error: The embedding service is not available."
        return error_gen(), []

    if not use_formatted_data: # RAG mode
        if not DB_DTIAS: # DTIAS is always required for RAG
            print(f"❌ SINGLE_QUERY: Global DTIAS Chroma DB (DB_DTIAS) not available for RAG.")
            def error_gen(): yield "Error: The primary documentation database (DTIAS) is not available."
            return error_gen(), []
        if use_cloudify_docs and not DB_CLOUDIFY:
            print(f"⚠️ SINGLE_QUERY: Cloudify docs requested for RAG, but DB_CLOUDIFY not available. Proceeding with DTIAS only.")

    else: # Formatted data mode
        if not ALL_RAG_DATA:
            print(f"❌ SINGLE_QUERY: Formatted data mode selected, but ALL_RAG_DATA not loaded.")
            def error_gen(): yield "Error: The formatted documentation content is not available."
            return error_gen(), []
        # For formatted data, an initial lookup is still done via get_contextual_chunks
        if not DB_DTIAS:
             print(f"❌ SINGLE_QUERY: DB_DTIAS not available for initial source lookup in formatted_data mode.")
             def error_gen(): yield "Error: The primary database (DTIAS) is not available for source lookup."
             return error_gen(), []
        if use_cloudify_docs and not DB_CLOUDIFY:
             print(f"⚠️ SINGLE_QUERY: Cloudify sources requested for formatted data lookup, but DB_CLOUDIFY not available. Proceeding with DTIAS sources only.")


    retrieved_sources = []
    context_text = ""
    context_docs = []

    if not use_formatted_data:
        # --- MODIFICATION: Use `text_to_embed` for the database search ---
        start_time_rag_retrieval = time.time()
        context_docs, retrieved_ids, retrieved_sources = get_contextual_chunks(
            DB_DTIAS,
            DB_CLOUDIFY if use_cloudify_docs else None,
            text_for_embedding_search=text_to_embed, # Use the optimized text for searching
            include_cloudify=use_cloudify_docs,
            k=k_val,
            window=4
        )
        end_time_rag_retrieval = time.time()
        print(f"SINGLE_QUERY: RAG Retrieval (get_contextual_chunks) completed in {end_time_rag_retrieval - start_time_rag_retrieval:.4f} seconds.")

        if not context_docs:
            print("❌ SINGLE_QUERY: No relevant context found in the database(s) for this query.")
            def empty_gen(): yield "I couldn't find relevant information in the documentation to answer your question."
            return empty_gen(), []

        start_time_context_format = time.time()
        context_pieces = []
        last_source_file = None
        for i, doc in enumerate(context_docs):
            current_source_file = doc.metadata.get("source")
            current_content = doc.page_content
            
            if i > 0:
                if current_source_file != last_source_file:
                    context_pieces.append("\n\n---\n\n")
                else:
                    context_pieces.append("\n\n")
            
            if doc.metadata.get("is_full_file"):
                context_pieces.append(f"[Full content from {current_source_file}]\n\n")
            
            context_pieces.append(current_content)
            last_source_file = current_source_file
        context_text = "".join(context_pieces)
        end_time_context_format = time.time()
        print(f"SINGLE_QUERY: Context text formatting completed in {end_time_context_format - start_time_context_format:.4f} seconds.")

    else: # use_formatted_data is True
        # --- MODIFICATION: Use `text_to_embed` for the database search ---
        start_time_formatted_lookup = time.time()
        temp_context_docs, _, _ = get_contextual_chunks(
            DB_DTIAS,
            DB_CLOUDIFY if use_cloudify_docs else None,
            text_for_embedding_search=text_to_embed, # Use the optimized text for searching
            include_cloudify=use_cloudify_docs,
            k=k_val,
            window=0
        )
        end_time_formatted_lookup = time.time()
        print(f"SINGLE_QUERY: Formatted data source lookup (via get_contextual_chunks) completed in {end_time_formatted_lookup - start_time_formatted_lookup:.4f} seconds.")

        if not temp_context_docs:
            print("❌ SINGLE_QUERY: No relevant base documents found for formatted data lookup from any active collection.")
            def empty_gen(): yield "I couldn't find base documents to retrieve formatted context."
            return empty_gen(), []

        start_time_formatted_build = time.time()
        context_text_pieces = ["The first page of API documentation is:\n\n"]
        unique_sources_used = set()
        for doc in temp_context_docs:
            source_url = doc.metadata.get("source")
            if source_url and source_url not in unique_sources_used:
                page_content = ALL_RAG_DATA.get(source_url, f"[Content for {source_url} not found in pre-loaded RagFormattedData.json]\n")
                context_text_pieces.append(page_content)
                context_text_pieces.append("\n\nThe next page of API documentation is:\n\n")
                unique_sources_used.add(source_url)

        if len(context_text_pieces) > 1:
            context_text = "".join(context_text_pieces[:-1])
        else:
            context_text = "No relevant formatted API documentation pages found."
        
        retrieved_sources = list(unique_sources_used)
        context_docs = [Document(page_content=ALL_RAG_DATA.get(src, ""), metadata={"source": src}) for src in retrieved_sources]
        end_time_formatted_build = time.time()
        print(f"SINGLE_QUERY: Formatted context text building completed in {end_time_formatted_build - start_time_formatted_build:.4f} seconds.")

    start_time_prompt_format = time.time()
    prompt_template = ChatPromptTemplate.from_template(PROMPT)
    # The `query_text` here is the full, human-readable (reframed) question
    prompt = prompt_template.format(context=context_text, question=query_text)
    end_time_prompt_format = time.time()
    print(f"SINGLE_QUERY: Prompt formatting completed in {end_time_prompt_format - start_time_prompt_format:.4f} seconds.")

    print("\n📝 SINGLE_QUERY: Sending Prompt to LLM:")
    print("-" * 30)
    num_docs_in_context = len(context_docs) if context_docs else 0
    print(f"Number of document sources/pages in context: {num_docs_in_context}")
    print(f"Context length (chars): {len(context_text)}")
    print(f"Query (for LLM): {query_text}")
    print("-" * 30)

    print("SINGLE_QUERY: Invoking LLM (stream)...")
    start_time_llm_invoke = time.time()
    try:
        response_stream = MODEL.stream(prompt)
        end_time_llm_invoke = time.time()
        print(f"✅ SINGLE_QUERY: LLM stream invocation completed in {end_time_llm_invoke - start_time_llm_invoke:.4f} seconds.")
    except Exception as e:
        end_time_llm_invoke = time.time()
        print(f"❌ SINGLE_QUERY: Error invoking LLM stream in {end_time_llm_invoke - start_time_llm_invoke:.4f} seconds: {e}")
        def error_gen(): yield f"There was an error generating the response stream: {e}"
        return error_gen(), retrieved_sources

    end_time_single_query = time.time()
    print(f"SINGLE_QUERY: Finished total execution in {end_time_single_query - start_time_single_query:.4f} seconds.")
    return response_stream, retrieved_sources

# --- Main execution for command line testing ---
def main():
    print("MAIN: Starting contextModel script...")
    start_time_main = time.time()

    parser = argparse.ArgumentParser(description="Query the AI Documentation Chatbot.")
    parser.add_argument("query_text", type=str, help="The question to ask the chatbot.")
    parser.add_argument("--formatted", action="store_true", help="Use formatted RAG data (pre-loaded JSON).")
    parser.add_argument("--include_cloudify", action="store_true", help="Include Cloudify API docs in the context search.")
    parser.add_argument("-k", "--k_val", type=int, default=4, help="Number of top documents to retrieve for context.")


    args = parser.parse_args()
    original_query_text = args.query_text
    use_formatted = args.formatted
    include_cloudify_flag = args.include_cloudify
    k_value = args.k_val


    if not MODEL or not EMBEDDING_FUNCTION:
        print("Critical error: Core models (LLM or Embedding) not initialized. Exiting.")
        return
    
    # DB checks based on mode
    if not use_formatted: # RAG mode
        if not DB_DTIAS:
            print("Critical error: DB_DTIAS not initialized for RAG mode. Exiting.")
            return
        if include_cloudify_flag and not DB_CLOUDIFY:
            print("Warning: --include_cloudify specified, but Cloudify DB (DB_CLOUDIFY) is not available. Proceeding with DTIAS docs only.")
    elif use_formatted: # Formatted data mode
        if not ALL_RAG_DATA:
            print("Critical error: Formatted data requested (--formatted) but not loaded. Exiting.")
            return
        if not DB_DTIAS:
             print("Critical error: DB_DTIAS not initialized for source lookup in --formatted mode. Exiting.")
             return
        if include_cloudify_flag and not DB_CLOUDIFY:
            print("Warning: --include_cloudify specified for --formatted mode, but Cloudify DB (DB_CLOUDIFY) is not available for source lookup. Will use DTIAS sources only.")

    # --- MODIFICATION: Call the query reframer ---
    # For this script, we'll assume an empty chat history.
    # In a real chatbot application, you would manage and pass the actual history here.
    chat_history = []
    print("\nMAIN: Calling query reframer...")
    reframed_query, embedding_text = reframe_query_with_history(original_query_text, chat_history)
    print("---")
    
    print(f"MAIN: Calling single_query for reframed query '{reframed_query}' with k={k_value}, include_cloudify={include_cloudify_flag}, formatted={use_formatted}...")
    # --- MODIFICATION: Pass both reframed query and embedding text to single_query ---
    response_stream, sources = single_query(
        query_text=reframed_query,
        text_to_embed=embedding_text,
        use_cloudify_docs=include_cloudify_flag,
        use_formatted_data=use_formatted,
        k_val=k_value
    )

    if response_stream:
        print("\nMAIN: RESPONSE STREAM from single_query:")
        full_response = ""
        start_time_main_stream_consume = time.time()
        first_chunk_main_received = False
        time_to_first_chunk_main = None

        for chunk_idx, chunk in enumerate(response_stream):
            if not first_chunk_main_received:
                end_time_first_chunk_main = time.time()
                time_to_first_chunk_main = end_time_first_chunk_main - start_time_main_stream_consume
                first_chunk_main_received = True
                print(f"\nMAIN: Time to first chunk received in main loop: {time_to_first_chunk_main:.4f} seconds.")
            
            if chunk_idx == 0 and isinstance(chunk, str) and chunk.startswith("Error:"):
                 print(f"\nERROR from single_query: {chunk}")
                 full_response = chunk
                 break

            print(chunk, end="", flush=True)
            full_response += chunk
        print()

        end_time_main_stream_consume = time.time()
        if time_to_first_chunk_main is not None:
             print(f"\nMAIN: Finished consuming response stream in {end_time_main_stream_consume - start_time_main_stream_consume:.4f} seconds.")
        elif not full_response:
             print("\nMAIN: No data received from the response stream.")


        if sources is not None:
            print("\n" + "-"*30)
            print("MAIN: Sources Used (Unique Document Sources):")
            if sources:
                pprint(sources)
            else:
                print("No specific sources were identified or used for this query (or an error occurred before source retrieval).")
            print("-" * 30 + "\n")
    else:
        print("MAIN: Failed to get a response stream or critical component missing (likely handled inside single_query).")

    end_time_main = time.time()
    print(f"MAIN: Script execution finished in {end_time_main - start_time_main:.4f} seconds.")


if __name__ == "__main__":
    main()