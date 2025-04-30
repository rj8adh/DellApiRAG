from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
# from langchain_ollama import OllamaLLM # Assuming OllamaLLM is correct import
# If using Langchain community standard:
from langchain_ollama import OllamaLLM
from embeddingsMain import get_embed_function # Assuming this correctly imports your function
from langchain.schema.document import Document
from pprint import pprint
import argparse
import json
import re # For parsing the chunk ID
import os # For checking path existence

# Constants
CHROMADATAPATH = 'chromaDb'

PROMPT = """
You are an AI Documentation Chatbot. Answer the question a user asked BASED ONLY ON THE FOLLOWING CONTEXT:

{context}

---

Answer the question based ONLY on the above context: {question}
"""

MODEL = OllamaLLM(model="phi4-mini") # Updated model name based on whatever model you want

# Parses the source and index from just the chunk id
def parse_chunk_id(chunk_id: str) -> tuple[str | None, int | None]: # Fancy return stuff
    """Parses the source and index from the chunk ID."""
    # I'm using the source:index format
    match = re.match(r"^(.*):(\d+)$", chunk_id)
    if match:
        source = match.group(1)
        index = int(match.group(2))
        return source, index
    return None, None

# Gets the neighboring chunks
def get_contextual_chunks(db: Chroma, query_text: str, k: int = 4, window: int = 1) -> tuple[list[Document], list[str], list[str]]: # Added list[str] for sources

    print(f"🔎 Initial search for top {k} chunks...")
    # 1. Initial Search (find the top k starting points)
    initial_results = db.similarity_search_with_score(query_text, k=k)

    if not initial_results:
        print("NO INITIAL RESULTS FOUND FOR THE QUERY")
        return [], [], []

    print(f"Found {len(initial_results)} initial results.")

    all_ids_to_fetch = set()
    original_top_k_ids = [] # Keep track of the centers for logging purposes

    # 2. Identify IDs for the top k chunks and their neighbors
    print(f"Identifying context window IDs for top {len(initial_results)} results (window={window})...")
    for i, (doc, score) in enumerate(initial_results):
        doc_id = doc.metadata.get("id")
        if not doc_id:
            print(f"WARNING: Initial result {i+1} is missing 'id' metadata. Skipping context window for this result.")
            continue # Skip this result if no ID

        source, index = parse_chunk_id(doc_id)
        if source is None or index is None:
            print(f"WARNING: Could not parse source/index from ID '{doc_id}' for initial result {i+1}. Skipping context window for this result.")
            continue # Skip if parsing fails

        print(f"   - Processing initial chunk {i+1}: ID='{doc_id}', Score={score:.4f}, Source='{source}', Index={index}")

        original_top_k_ids.append(doc_id) # Add the center ID

        # Add the main chunk ID itself
        all_ids_to_fetch.add(doc_id)

        # Add neighbor chunks (before and after) within the window
        for offset in range(-window, window + 1):
            if offset == 0: # Already added the main ID
                continue
            neighbor_index = index + offset
            if neighbor_index >= 0: # Ensure index is not negative
                neighbor_id = f"{source}:{neighbor_index}"
                all_ids_to_fetch.add(neighbor_id)
            # Chroma's .get() handles non-existent IDs for us

    if not all_ids_to_fetch:
        print("WARNING: No valid chunk IDs identified after processing initial results.")
        return [], [], []

    list_ids_to_fetch = list(all_ids_to_fetch)
    print(f"Attempting to fetch {len(list_ids_to_fetch)} unique IDs for context: {list_ids_to_fetch}")

    # Retrieving the chunks based of their ids
    try:
        retrieved_data = db.get(ids=list_ids_to_fetch, include=["documents", "metadatas"])
        retrieved_ids_actual = retrieved_data.get('ids', [])
        print(f"ℹ️ Successfully retrieved {len(retrieved_ids_actual)} chunks by ID.")
    except Exception as e:
        print(f"WARNING: Error retrieving chunks by ID: {e}. Returning empty results.")
        return [], [], []

    if not retrieved_ids_actual:
        print("WARNING: db.get returned no documents despite requesting IDs.")
        return [], [], []


    # Sorting and setting up the documents
    # Making a dictionary for quick lookup of retrieved docs
    docs_by_id = {
        id_val: Document(page_content=doc, metadata=meta)
        for id_val, doc, meta in zip(retrieved_ids_actual, retrieved_data.get('documents', []), retrieved_data.get('metadatas', []))
        if id_val and doc is not None and meta is not None # Basic validation
    }

    # Build the final list of documents from the successfully retrieved data
    # Ensure we only include documents that were actually retrieved
    context_docs = [docs_by_id[doc_id] for doc_id in retrieved_ids_actual if doc_id in docs_by_id]

    # Sort the documents by source, then index in source
    def sort_key(doc):
        doc_id = doc.metadata.get("id", "") # Get ID safely
        source, index = parse_chunk_id(doc_id)
        # Using default values if parsing fails or metadata missing
        source_val = source if source is not None else ""
        index_val = index if index is not None else -1
        # Sorting by (source, index)
        return (source_val, index_val)

    context_docs.sort(key=sort_key)

    # Extracting sorted IDs and sources for the return value
    sorted_retrieved_ids = [doc.metadata.get("id", "N/A") for doc in context_docs] # Handle missing ID
    # Use a set to get unique sources in the order they appear after sorting
    unique_sorted_sources = list(dict.fromkeys(doc.metadata.get("source", "N/A") for doc in context_docs)) # Handle missing source


    print(f"✅ Retrieved and sorted {len(context_docs)} contextual documents.")
    # print(f"Sorted IDs: {sorted_retrieved_ids}")

    return context_docs, sorted_retrieved_ids, unique_sorted_sources # Return unique sources


# Not using formatted data means it's only relying on rag and nearest neighbors (the use_formatted_data kind of sucks right now)
# Using formatted data means that it is using the definitions straight from the database after finding the relevant urls
def single_query(query_text: str, use_formatted_data: bool = False):

    # Preparing the database connection (vector store)
    if not os.path.exists(CHROMADATAPATH):
        print(f"❌ Chroma DB path not found at {CHROMADATAPATH}. Please run the embedding script first.")
        return None

    try:
        embedding_function = get_embed_function()
        db = Chroma(persist_directory=CHROMADATAPATH, embedding_function=embedding_function)
        print("✅ Chroma DB connection established.")
    except Exception as e:
        print(f"❌ Failed to connect to Chroma DB at {CHROMADATAPATH}: {e}")
        return None # Cannot proceed without DB

    # Searching the data using our contextual retrieval function
    print(f"\n🔎 Searching for chunks related to: '{query_text}'")
    # k value means how many chunks we're getting, window is how many nearby chunks we're using for context
    if (not use_formatted_data):
        context_docs, retrieved_ids, retrieved_sources = get_contextual_chunks(db, query_text, k=4, window=4)
        if not context_docs:
            print("❌ No relevant context found in the database for this query.")
            return "I couldn't find relevant information in the documentation to answer your question."

        # Constructing the context string so that neighbors from the same page are in one section (reduces hallucinations and makes it easier for the model)
        context_pieces = []
        last_source = None
        for i, doc in enumerate(context_docs):
            current_source = doc.metadata.get("source") # Get the source of the current doc
            current_content = doc.page_content

            if i > 0: # Check if this is not the first document
                # If the source changed from the last document, add the '---' separator
                if current_source != last_source:
                    context_pieces.append("\n\n---\n\n")
                # If the source is the same, just add a newline break for readability
                elif current_source == last_source:
                     context_pieces.append("\n\n") # Newline break for same source

            context_pieces.append(current_content) # Add the actual content
            last_source = current_source # Update the last source seen

        context_text = "".join(context_pieces) # Join all pieces together

    else:
        with open("ScrapingStuff/storedData/RagFormattedData.json", 'r') as f:
            allRagData = json.load(f)

        context_docs, retrieved_ids, retrieved_sources = get_contextual_chunks(db, query_text, k=2, window=0) # context_docs needed for count later
        context_text = "The first page of api documentation is:\n\n"
        unique_sources = set() # Keeping track of unique sources used here
        for doc in context_docs: # Iterating through docs to get sources
             source = doc.metadata.get("source")
             if source and source not in unique_sources:
                 context_text += allRagData.get(source, f"[Content for {source} not found in RagFormattedData.json]\n") # Safely get data
                 context_text += "\n\nThe next page of api documentation is:\n\n"
                 unique_sources.add(source)

        context_text = context_text.removesuffix("\n\nThe next page of api documentation is:\n\n")
        # Making sure retrieved_sources reflects the unique sources actually used
        retrieved_sources = list(unique_sources)


    # Formatting the prompt for the LLM
    prompt_template = ChatPromptTemplate.from_template(PROMPT)
    prompt = prompt_template.format(context=context_text, question=query_text)

    # Just stuff to see the output
    print("\n📝 Sending Prompt to LLM:")
    # print("--- CONTEXT START ---")
    # print(context_text[:1000] + "..." if len(context_text) > 1000 else context_text) # Print start of context
    # print("--- CONTEXT END ---")
    print("-" * 30)
    print(f"Number of chunks in context: {len(context_docs)}") # Use len(context_docs) reliably
    print(f"Context length (chars): {len(context_text)}")
    print(f"Query: {query_text}")
    print("-" * 30)
    print("PROMPT:\n")
    print(prompt)


    # Getting the response from the Language Model
    # The LLM reads the context and answers the question
    print("🧠 Invoking LLM...")

    try:
        response_text = MODEL.invoke(prompt) # Calls the llm using the prompt we have
        print("✅ LLM invocation successful.")
    except Exception as e:
        print(f"❌ Error invoking LLM: {e}")
        return "There was an error generating the response."


    # Formatting and printing the final response and sources
    formatted_response = f"\nRESPONSE:\n{response_text}\n"
    print(formatted_response)
    pprint(f"Sources Used (Unique Document Sources): {retrieved_sources}\n") # Display unique sources
    if db is not None: del db # Deleting the database reference before the text is returned so it doesn't take forever to execute the code
    return response_text

def main():
    # Setting up command-line argument stuff
    # This allows running the code like: python contextModel.py "blahblahblah"
    parser = argparse.ArgumentParser(description="Query the AI Documentation Chatbot.")
    parser.add_argument("query_text", type=str, help="The question to ask the chatbot.")



    # Added the argument for formatted data flag
    parser.add_argument("-f", "--formatted", action="store_true", help="Use pre-formatted data instead of raw RAG chunks.")
    args = parser.parse_args()
    query_text = args.query_text # Get the question from the arguments

    # Executing the query stuff with the formatted flags
    single_query(query_text, use_formatted_data=args.formatted)

if __name__ == "__main__":
    main() # Good practice to do this instead of putting all of main's code inside this if