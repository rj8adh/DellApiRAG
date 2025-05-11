# contextModel.py

import sys
import time # Import the time module
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from embeddingsMain import get_embed_function # Assuming this is efficient or also caches
from langchain.schema.document import Document
from pprint import pprint
import argparse
import json
import re
import os

# --- Constants ---
CHROMADATAPATH = 'chromaDb'
RAG_FORMATTED_DATA_PATH = "ScrapingStuff/storedData/RagFormattedData.json" # Define path for JSON data

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
start_time_global_init = time.time() # Start timer for global init

# 1. LLM Model
try:
    # MODEL = OllamaLLM(model="phi3:mini", temperature=.3)
    MODEL = OllamaLLM(model="qwen2.5:14b", temperature=.3)
    # MODEL = OllamaLLM(model="qwen2.5:14b-instruct-q4_K_M", temperature=.3) # Using the quantized model to make it run faster
    # MODEL = OllamaLLM(model="qwen2.5:14b-instruct-q4_K_S", temperature=.3)
    # qwen2.5:14b-instruct-q4_K_S
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

# 3. ChromaDB Connection
DB = None # Initialize DB as None
if EMBEDDING_FUNCTION and os.path.exists(CHROMADATAPATH):
    try:
        DB = Chroma(persist_directory=CHROMADATAPATH, embedding_function=EMBEDDING_FUNCTION)
        print(f"✅ Global Chroma DB connection (DB) established to {CHROMADATAPATH}.")
    except Exception as e:
        DB = None
        print(f"❌ Failed to establish global Chroma DB connection (DB): {e}")
elif not os.path.exists(CHROMADATAPATH):
    print(f"⚠️ Global Chroma DB path not found at {CHROMADATAPATH}. DB not initialized.")
elif not EMBEDDING_FUNCTION:
    print(f"⚠️ Embedding function not available. DB not initialized.")


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

end_time_global_init = time.time() # End timer for global init
print(f"CONTEXT_MODEL.PY: Global resource initialization complete in {end_time_global_init - start_time_global_init:.4f} seconds.")
# --- End of Global Initialization ---


def parse_chunk_id(chunk_id: str) -> tuple[str | None, int | None]:
    match = re.match(r"^(.*):(\d+)$", chunk_id)
    if match:
        source = match.group(1)
        index = int(match.group(2))
        return source, index
    return None, None

def get_contextual_chunks(db_conn: Chroma | None, query_text: str, k: int = 4, window: int = 1) -> tuple[list[Document], list[str], list[str]]:
    print("\nGET_CONTEXTUAL_CHUNKS: Starting...")
    start_time_get_contextual = time.time()

    if not db_conn: # Check if db_conn is None
        print("❌ GET_CONTEXTUAL_CHUNKS: DB connection is not available.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (DB not available) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    # ... (rest of your get_contextual_chunks function, ensure it uses the passed db_conn) ...
    print(f"🔎 GET_CONTEXTUAL_CHUNKS: Initial search for top {k} chunks...")
    start_time_search = time.time()
    initial_results = db_conn.similarity_search_with_score(query_text, k=k) # Use db_conn
    end_time_search = time.time()
    print(f"GET_CONTEXTUAL_CHUNKS: Similarity search completed in {end_time_search - start_time_search:.4f} seconds.")

    if not initial_results:
        print("❌ GET_CONTEXTUAL_CHUNKS: NO INITIAL RESULTS FOUND FOR THE QUERY")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (no initial results) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    print(f"GET_CONTEXTUAL_CHUNKS: Found {len(initial_results)} initial results.")

    all_ids_to_fetch = set()
    original_top_k_ids = []

    print(f"GET_CONTEXTUAL_CHUNKS: Identifying context window IDs for top {len(initial_results)} results (window={window})...")
    start_time_identify_ids = time.time()
    for i, (doc, score) in enumerate(initial_results):
        doc_id = doc.metadata.get("id")
        if not doc_id:
            print(f"WARNING: Initial result {i+1} is missing 'id' metadata. Skipping context window for this result.")
            continue

        source, index = parse_chunk_id(doc_id)
        if source is None or index is None:
            print(f"WARNING: Could not parse source/index from ID '{doc_id}' for initial result {i+1}. Skipping context window for this result.")
            continue

        # print(f"   - Processing initial chunk {i+1}: ID='{doc_id}', Score={score:.4f}, Source='{source}', Index={index}") # Too verbose
        original_top_k_ids.append(doc_id)
        all_ids_to_fetch.add(doc_id)

        for offset in range(-window, window + 1):
            if offset == 0:
                continue
            neighbor_index = index + offset
            if neighbor_index >= 0:
                neighbor_id = f"{source}:{neighbor_index}"
                all_ids_to_fetch.add(neighbor_id)

    end_time_identify_ids = time.time()
    print(f"GET_CONTEXTUAL_CHUNKS: Identified {len(all_ids_to_fetch)} potential context IDs in {end_time_identify_ids - start_time_identify_ids:.4f} seconds.")

    if not all_ids_to_fetch:
        print("WARNING: No valid chunk IDs identified after processing initial results.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (no valid IDs) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    list_ids_to_fetch = list(all_ids_to_fetch)
    print(f"GET_CONTEXTUAL_CHUNKS: Attempting to fetch {len(list_ids_to_fetch)} unique IDs...")

    try:
        start_time_get_ids = time.time()
        retrieved_data = db_conn.get(ids=list_ids_to_fetch, include=["documents", "metadatas"]) # Use db_conn
        retrieved_ids_actual = retrieved_data.get('ids', [])
        end_time_get_ids = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Successfully retrieved {len(retrieved_ids_actual)} chunks by ID in {end_time_get_ids - start_time_get_ids:.4f} seconds.")
    except Exception as e:
        print(f"❌ GET_CONTEXTUAL_CHUNKS: Error retrieving chunks by ID: {e}. Returning empty results.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (retrieval error) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    if not retrieved_ids_actual:
        print("WARNING: db.get returned no documents despite requesting IDs.")
        end_time_get_contextual = time.time()
        print(f"GET_CONTEXTUAL_CHUNKS: Finished (db.get returned empty) in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
        return [], [], []

    start_time_process_retrieved = time.time()
    docs_by_id = {
        id_val: Document(page_content=doc, metadata=meta)
        for id_val, doc, meta in zip(retrieved_ids_actual, retrieved_data.get('documents', []), retrieved_data.get('metadatas', []))
        if id_val and doc is not None and meta is not None
    }
    context_docs = [docs_by_id[doc_id] for doc_id in retrieved_ids_actual if doc_id in docs_by_id]

    def sort_key(doc):
        doc_id = doc.metadata.get("id", "")
        source, index = parse_chunk_id(doc_id)
        source_val = source if source is not None else ""
        index_val = index if index is not None else -1
        return (source_val, index_val)

    context_docs.sort(key=sort_key)
    sorted_retrieved_ids = [doc.metadata.get("id", "N/A") for doc in context_docs]
    unique_sorted_sources = list(dict.fromkeys(doc.metadata.get("source", "N/A") for doc in context_docs))

    end_time_process_retrieved = time.time()
    print(f"✅ GET_CONTEXTUAL_CHUNKS: Retrieved and sorted {len(context_docs)} contextual documents in {end_time_process_retrieved - start_time_process_retrieved:.4f} seconds.")

    end_time_get_contextual = time.time()
    print(f"GET_CONTEXTUAL_CHUNKS: Finished total execution in {end_time_get_contextual - start_time_get_contextual:.4f} seconds.")
    return context_docs, sorted_retrieved_ids, unique_sorted_sources


def single_query(query_text: str, use_formatted_data: bool = False, k_val:int = 4):
    print(f"\nSINGLE_QUERY: Starting for query: '{query_text}' | use_formatted_data: {use_formatted_data}")
    start_time_single_query = time.time()

    # --- Check if global resources are available ---
    if not MODEL:
        print("❌ SINGLE_QUERY: Global LLM (MODEL) not available.")
        end_time_single_query = time.time()
        print(f"SINGLE_QUERY: Finished (LLM not available) in {end_time_single_query - start_time_single_query:.4f} seconds.")
        def error_gen(): yield "Error: The AI model is not available."
        return error_gen(), []

    if not EMBEDDING_FUNCTION: # Though DB check often implies this
        print("❌ SINGLE_QUERY: Global EMBEDDING_FUNCTION not available.")
        end_time_single_query = time.time()
        print(f"SINGLE_QUERY: Finished (Embeddings not available) in {end_time_single_query - start_time_single_query:.4f} seconds.")
        def error_gen(): yield "Error: The embedding service is not available."
        return error_gen(), []

    if not DB and not use_formatted_data: # If not using formatted_data, DB is essential
        print(f"❌ SINGLE_QUERY: Global Chroma DB (DB) not available and not using formatted_data mode.")
        end_time_single_query = time.time()
        print(f"SINGLE_QUERY: Finished (DB not available for RAG) in {end_time_single_query - start_time_single_query:.4f} seconds.")
        def error_gen(): yield "Error: The documentation database is not available."
        return error_gen(), []

    if use_formatted_data and not ALL_RAG_DATA:
        print(f"❌ SINGLE_QUERY: Formatted data mode selected, but ALL_RAG_DATA not loaded.")
        end_time_single_query = time.time()
        print(f"SINGLE_QUERY: Finished (Formatted data not loaded) in {end_time_single_query - start_time_single_query:.4f} seconds.")
        def error_gen(): yield "Error: The formatted documentation content is not available."
        return error_gen(), []

    # No longer need to initialize DB, EMBEDDING_FUNCTION here.
    # Just use the global DB and ALL_RAG_DATA.

    retrieved_sources = []
    context_text = ""
    context_docs = [] # Ensure it's initialized

    if not use_formatted_data:
        if not DB: # Redundant check if above checks are solid, but good for safety
            print("❌ SINGLE_QUERY: No DB connection available for RAG mode.")
            end_time_single_query = time.time()
            print(f"SINGLE_QUERY: Finished (DB not available for RAG path) in {end_time_single_query - start_time_single_query:.4f} seconds.")
            def error_gen(): yield "Database not available for search."
            return error_gen(), []
        # Pass the global DB connection to get_contextual_chunks
        start_time_rag_retrieval = time.time()
        context_docs, retrieved_ids, retrieved_sources = get_contextual_chunks(DB, query_text, k=k_val, window=4)
        end_time_rag_retrieval = time.time()
        print(f"SINGLE_QUERY: RAG Retrieval (get_contextual_chunks) completed in {end_time_rag_retrieval - start_time_rag_retrieval:.4f} seconds.")

        if not context_docs:
            print("❌ SINGLE_QUERY: No relevant context found in the database for this query.")
            end_time_single_query = time.time()
            print(f"SINGLE_QUERY: Finished (no context found) in {end_time_single_query - start_time_single_query:.4f} seconds.")
            def empty_gen(): yield "I couldn't find relevant information in the documentation to answer your question."
            return empty_gen(), []

        start_time_context_format = time.time()
        context_pieces = []
        last_source = None
        for i, doc in enumerate(context_docs):
            current_source = doc.metadata.get("source")
            current_content = doc.page_content
            if i > 0:
                if current_source != last_source:
                    context_pieces.append("\n\n---\n\n")
                elif current_source == last_source:
                    context_pieces.append("\n\n")
            context_pieces.append(current_content)
            last_source = current_source
        context_text = "".join(context_pieces)
        end_time_context_format = time.time()
        print(f"SINGLE_QUERY: Context text formatting completed in {end_time_context_format - start_time_context_format:.4f} seconds.")

    else: # use_formatted_data is True
        if not ALL_RAG_DATA: # Check if global data is loaded
             print("❌ SINGLE_QUERY: RagFormattedData.json was not loaded globally.")
             end_time_single_query = time.time()
             print(f"SINGLE_QUERY: Finished (formatted data not loaded) in {end_time_single_query - start_time_single_query:.4f} seconds.")
             def error_gen(): yield "Error: Formatted data file not available."
             return error_gen(), []

        # Need to perform a lightweight search to find relevant source URLs first
        # We pass k=1 and window=0 because we only need the source URLs from the top few documents
        # to then look up in ALL_RAG_DATA.
        # Ensure DB is available even for this minimal lookup if your logic requires it.
        if not DB:
            print("❌ SINGLE_QUERY: DB connection needed for initial source lookup in formatted_data mode.")
            end_time_single_query = time.time()
            print(f"SINGLE_QUERY: Finished (DB not available for lookup) in {end_time_single_query - start_time_single_query:.4f} seconds.")
            def error_gen(): yield "Database not available for initial source lookup."
            return error_gen(), []

        start_time_formatted_lookup = time.time()
        temp_context_docs, _, _ = get_contextual_chunks(DB, query_text, k=k_val, window=0) # Small k, window=0
        end_time_formatted_lookup = time.time()
        print(f"SINGLE_QUERY: Formatted data source lookup (via get_contextual_chunks) completed in {end_time_formatted_lookup - start_time_formatted_lookup:.4f} seconds.")

        if not temp_context_docs:
            print("❌ SINGLE_QUERY: No relevant base documents found for formatted data lookup.")
            end_time_single_query = time.time()
            print(f"SINGLE_QUERY: Finished (no base docs for lookup) in {end_time_single_query - start_time_single_query:.4f} seconds.")
            def empty_gen(): yield "I couldn't find base documents to retrieve formatted context."
            return empty_gen(), []

        start_time_formatted_build = time.time()
        context_text_pieces = ["The first page of api documentation is:\n\n"]
        unique_sources_used = set()
        for doc in temp_context_docs:
            source_url = doc.metadata.get("source")
            if source_url and source_url not in unique_sources_used:
                # Use the pre-loaded ALL_RAG_DATA
                page_content = ALL_RAG_DATA.get(source_url, f"[Content for {source_url} not found in pre-loaded RagFormattedData.json]\n")
                context_text_pieces.append(page_content)
                context_text_pieces.append("\n\nThe next page of api documentation is:\n\n")
                unique_sources_used.add(source_url)

        # Remove the last "next page" separator
        if len(context_text_pieces) > 1: # ensure there was at least one page added
            context_text = "".join(context_text_pieces[:-1]) # Join all but the last "next page"
        else: # only the initial header, meaning no docs were actually added
            context_text = "No relevant formatted API documentation pages found."

        retrieved_sources = list(unique_sources_used)
        # Note: context_docs here refers to the small set from temp_context_docs for source extraction,
        # not the full content from JSON. If you need to represent the JSON content as Document objects,
        # you'd need to construct them. For now, context_text directly holds the content.
        # For consistency, if you need context_docs to reflect the formatted data:
        context_docs = [Document(page_content=ALL_RAG_DATA.get(src, ""), metadata={"source": src}) for src in retrieved_sources]
        end_time_formatted_build = time.time()
        print(f"SINGLE_QUERY: Formatted context text building completed in {end_time_formatted_build - start_time_formatted_build:.4f} seconds.")


    start_time_prompt_format = time.time()
    prompt_template = ChatPromptTemplate.from_template(PROMPT)
    prompt = prompt_template.format(context=context_text, question=query_text)
    end_time_prompt_format = time.time()
    print(f"SINGLE_QUERY: Prompt formatting completed in {end_time_prompt_format - start_time_prompt_format:.4f} seconds.")

    print("\n📝 SINGLE_QUERY: Sending Prompt to LLM:")
    print("-" * 30)
    # Use a reliable way to count actual documents used for context, which might be different for the two modes
    num_docs_in_context = len(context_docs) if context_docs else 0
    print(f"Number of document sources/pages in context: {num_docs_in_context}")
    print(f"Context length (chars): {len(context_text)}")
    print(f"Query: {query_text}")
    # print(f"\nFull Prompt:\n{prompt}\n") # Uncomment for debugging the full prompt
    print("-" * 30)

    print("SINGLE_QUERY: Invoking LLM (stream)...")
    start_time_llm_invoke = time.time()
    try:
        response_stream = MODEL.stream(prompt)
        end_time_llm_invoke = time.time()
        print(f"✅ SINGLE_QUERY: LLM stream invocation (time until generator ready) completed in {end_time_llm_invoke - start_time_llm_invoke:.4f} seconds.")
    except Exception as e:
        end_time_llm_invoke = time.time() # Still record time even on error
        print(f"❌ SINGLE_QUERY: Error invoking LLM stream in {end_time_llm_invoke - start_time_llm_invoke:.4f} seconds: {e}")
        end_time_single_query = time.time() # End timer for single_query on error
        print(f"SINGLE_QUERY: Finished (LLM invoke error) in {end_time_single_query - start_time_single_query:.4f} seconds.")
        def error_gen(): yield f"There was an error generating the response stream: {e}"
        return error_gen(), retrieved_sources # retrieved_sources might be from RAG path

    # Removed 'del db' as DB is now global and managed outside this function's lifecycle
    end_time_single_query = time.time()
    print(f"SINGLE_QUERY: Finished total execution in {end_time_single_query - start_time_single_query:.4f} seconds.")
    return response_stream, retrieved_sources

# --- Main execution for command line testing ---
def main():
    print("MAIN: Starting contextModel script...")
    start_time_main = time.time()

    parser = argparse.ArgumentParser(description="Query the AI Documentation Chatbot.")
    parser.add_argument("query_text", type=str, help="The question to ask the chatbot.")
    parser.add_argument("--formatted", action="store_true", help="Use formatted RAG data.") # Added option

    args = parser.parse_args()
    query_text = args.query_text
    use_formatted = args.formatted # Get the flag

    # Ensure global resources are loaded before first query,
    # which they will be if this script is run directly or imported.
    # The global initialization block runs automatically on import.
    if not MODEL or not EMBEDDING_FUNCTION:
        print("Critical error: Core models (LLM or Embedding) not initialized. Exiting.")
        end_time_main = time.time()
        print(f"MAIN: Finished (critical init error) in {end_time_main - start_time_main:.4f} seconds.")
        return
    if not DB and not use_formatted:
         print("Critical error: DB not initialized and not using formatted data. Exiting.")
         end_time_main = time.time()
         print(f"MAIN: Finished (critical DB error) in {end_time_main - start_time_main:.4f} seconds.")
         return
    if use_formatted and not ALL_RAG_DATA:
         print("Critical error: Formatted data requested but not loaded. Exiting.")
         end_time_main = time.time()
         print(f"MAIN: Finished (critical formatted data error) in {end_time_main - start_time_main:.4f} seconds.")
         return


    print(f"MAIN: Calling single_query for query '{query_text}'...")
    # single_query has its own internal timers now
    response_stream, sources = single_query(query_text, use_formatted_data=use_formatted)

    if response_stream:
        print("\nMAIN: RESPONSE STREAM from single_query:")
        full_response = ""
        start_time_main_stream_consume = time.time()
        first_chunk_main_received = False
        time_to_first_chunk_main = None

        # Consume the stream and time the first chunk receipt in main
        for chunk in response_stream:
            if not first_chunk_main_received:
                 end_time_first_chunk_main = time.time()
                 time_to_first_chunk_main = end_time_first_chunk_main - start_time_main_stream_consume
                 first_chunk_main_received = True
                 print(f"\nMAIN: Time to first chunk received in main loop: {time_to_first_chunk_main:.4f} seconds.")

            print(chunk, end="", flush=True) # print chunks as they arrive
            full_response += chunk
        print() # Newline after the stream finishes

        end_time_main_stream_consume = time.time()
        print(f"\nMAIN: Finished consuming response stream in {end_time_main_stream_consume - start_time_main_stream_consume:.4f} seconds.")


        if sources is not None:
            print("\n" + "-"*30)
            print("MAIN: Sources Used (Unique Document Sources):")
            pprint(sources)
            print("-" * 30 + "\n")
    else:
        print("MAIN: Failed to get a response stream or critical component missing (handled inside single_query).")

    end_time_main = time.time()
    print(f"MAIN: Script execution finished in {end_time_main - start_time_main:.4f} seconds.")


if __name__ == "__main__":
    main()