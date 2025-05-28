import re
import json
from typing import List, Dict, Any, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema.document import Document
import torch
import os
import shutil
import stat
from tqdm import tqdm # Import tqdm for progress bars

# --- Configuration Constants ---
CHROMADATAPATH = 'chromaDb' # Base path for the Chroma database
MODEL_NAME = "Alibaba-NLP/gte-Qwen2-1.5B-instruct" # Embedding model
CHROMA_ADD_BATCH_SIZE = 50 # Batch size for adding documents to ChromaDB
CLOUDIFY_DOCS_DIR = "ScrapingStuff/storedData/cloudify-rest-docs" # Directory for Cloudify markdown docs

# Check PyTorch version and CUDA availability
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

# Determine device for embeddings (prefer CUDA if available, otherwise CPU)
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEVICE = "cpu"
print(f"Using device: {DEVICE}") # Confirm which device is used

# Embedding Function
def get_embed_function():
    """
    Returns a HuggingFaceEmbeddings instance configured for the specified model.
    """
    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': DEVICE, 'trust_remote_code': True},
        encode_kwargs={'normalize_embeddings': False}
    )

# --- Markdown Parsing for Contextual Chunks (Copied from previous immersive) ---
def parse_markdown_for_contextual_chunks(markdown_content: str, source_file: str = "unknown_source.md") -> List[Dict[str, Any]]:
    """
    Parses markdown content into contextual chunks.
    Each chunk represents a logical section of the documentation, typically
    starting with a top-level heading (#, ##, ###) and including all subsequent
    related content (paragraphs, lists, tables, code blocks, example blocks)
    until the next major heading or the end of the document.

    Args:
        markdown_content (str): The full Markdown content as a string.
        source_file (str): The name or path of the source Markdown file, for metadata.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                               represents a contextual chunk and contains:
                               - 'text': The raw Markdown content of the chunk, *excluding* its initial heading.
                               - 'heading': The main heading (H1) of the section.
                               - 'sub_heading': The sub-heading (H2) of the chunk.
                               - 'source_file': The original file this chunk came from.
    """
    chunks = []
    lines = markdown_content.split('\n')

    current_chunk_lines = []
    current_heading = "" # Stores the most recent H1 heading
    current_sub_heading = "" # Stores the most recent H2 heading (or H3 if no H2)
    in_code_block = False
    in_example_block = False

    heading_pattern = re.compile(r"^(#+)\s*(.*)$")
    code_block_delimiter_pattern = re.compile(r"^\s*```")
    example_block_start_pattern = re.compile(r"^\s*> (Request|Response) Example")
    front_matter_delimiter_pattern = re.compile(r"^\s*---")

    def finalize_chunk():
        if current_chunk_lines:
            chunk_text = "\n".join(current_chunk_lines).strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "heading": current_heading,
                    "sub_heading": current_sub_heading,
                    "source_file": source_file,
                })

    in_front_matter = False

    for i, line in enumerate(lines):
        stripped_line = line.strip()

        if front_matter_delimiter_pattern.match(stripped_line):
            if not in_front_matter:
                in_front_matter = True
            else:
                in_front_matter = False
            continue

        if in_front_matter:
            continue

        if code_block_delimiter_pattern.match(stripped_line):
            in_code_block = not in_code_block
            current_chunk_lines.append(line)
            continue

        if in_code_block:
            current_chunk_lines.append(line)
            continue

        if example_block_start_pattern.match(stripped_line):
            in_example_block = True
            current_chunk_lines.append(line)
            continue

        if in_example_block:
            current_chunk_lines.append(line)
            if stripped_line == "" and (i + 1 < len(lines) and not lines[i+1].startswith(">")):
                in_example_block = False
            continue

        match = heading_pattern.match(line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()

            if level <= 2: # New H1 or H2 means a new logical section
                finalize_chunk() # Save the previous chunk
                current_chunk_lines = [] # Reset for the new chunk

                if level == 1:
                    current_heading = text
                    current_sub_heading = "" # Reset sub-heading when a new H1 starts
                elif level == 2:
                    current_sub_heading = text

            else: # For H3 and deeper, they are part of the current H2's context
                current_chunk_lines.append(line) # These sub-headings are part of the chunk text
        else:
            current_chunk_lines.append(line)

    finalize_chunk()
    return chunks


# Building the page_content with prepended headings
def generate_docs_from_contextual_chunks(contextual_chunks: List[Dict[str, Any]], base_source_name: str) -> List[Document]:
    """
    Converts a list of dictionaries (from parse_markdown_for_contextual_chunks)
    into a list of LangChain Document objects. Prepends heading/subheading to the
    page_content for embedding context.

    Args:
        contextual_chunks (List[Dict[str, Any]]): List of parsed markdown chunks.
        base_source_name (str): A base name to prepend to the source_file for uniqueness.

    Returns:
        List[Document]: A list of LangChain Document objects.
    """
    documents = []
    if not contextual_chunks:
        print("Warning: No contextual chunks provided to generate_docs_from_contextual_chunks.")
        return documents

    print(f"Generating LangChain Documents from {len(contextual_chunks)} contextual chunks...")
    for i, chunk in enumerate(contextual_chunks):
        full_content_parts = []
        if chunk.get("heading"):
            full_content_parts.append(f"# {chunk['heading']}")
        if chunk.get("sub_heading"):
            full_content_parts.append(f"## {chunk['sub_heading']}")

        # Add the main text content, which now correctly excludes the top-level heading
        full_content_parts.append(chunk["text"])

        source_id = f"{base_source_name}/{chunk['source_file']}#{i}"
        doc = Document(
            page_content="\n".join(full_content_parts).strip(),
            metadata={
                "source": source_id,
                "heading": chunk.get("heading", ""),
                "sub_heading": chunk.get("sub_heading", ""),
                # Add other metadata if desired
            }
        )
        documents.append(doc)
    print(f"Generated {len(documents)} Document objects from contextual chunks.")
    return documents

# Adding stuff the chroma database (also has progress bar)
def add_to_chroma(chunks: list[Document], collection_name: str):
    """
    Adds a list of LangChain Document chunks to a specified ChromaDB collection.
    Includes a progress bar for batch processing.

    Args:
        chunks (list[Document]): A list of LangChain Document objects to add.
        collection_name (str): The name of the ChromaDB collection to add documents to.
    """
    print(f"Connecting to ChromaDB collection: '{collection_name}' at {CHROMADATAPATH}")
    # Setting up the database connection with a specific collection name
    db = Chroma(
        persist_directory=CHROMADATAPATH,
        embedding_function=get_embed_function(),
        collection_name=collection_name # Specify the collection name here
    )

    # Ensure chunks have unique IDs before checking existing ones
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Checking existing documents in the specific collection
    try:
        # Fetching existing IDs from the specified collection
        # Note: A large number of existing documents can make this call slow.
        existing_items = db.get(ids=[c.metadata.get("id") for c in chunks_with_ids if c.metadata.get("id")], include=[])
        existing_ids = set(existing_items["ids"])
        print(f"Number of existing documents in collection '{collection_name}': {len(existing_ids)}")
    except Exception as e:
        print(f"Warning: Could not get existing items from collection '{collection_name}', assuming it's empty or needs rebuild: {e}")
        existing_ids = set()

    # Getting new chunks ready
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata.get("id") not in existing_ids:
            new_chunks.append(chunk)

    # Adding the new chunks to the database
    if len(new_chunks):
        print(f"Adding {len(new_chunks)} new documents to collection '{collection_name}' in batches of {CHROMA_ADD_BATCH_SIZE}...")

        for i in tqdm(range(0, len(new_chunks), CHROMA_ADD_BATCH_SIZE), desc=f"Adding to {collection_name}"):
            batch = new_chunks[i:i + CHROMA_ADD_BATCH_SIZE]
            if not batch:
                continue

            batch_ids = [chunk.metadata["id"] for chunk in batch]

            try:
                db.add_documents(batch, ids=batch_ids)
            except Exception as e:
                print(f"\nError adding batch starting at index {i} to collection '{collection_name}': {e}")

        print(f"✅ New documents added successfully to collection '{collection_name}'.")

    else:
        print(f"✅ No new documents to add to collection '{collection_name}'.")

    return db # Return the database client for the specific collection


# Calculates and assigns unique chunk ids
def calculate_chunk_ids(chunks: list[Document]):
    """
    Calculates and assigns unique IDs to each document chunk based on its source.
    Format: 'source_file_name:chunk_index'.
    """
    last_source = None
    chunk_index = 0
    for chunk in chunks:
        # Use 'source' from metadata if available, otherwise 'unknown_source'
        # For Cloudify docs, 'source' will include 'base_source_name/source_file#index'
        source = chunk.metadata.get("source", "unknown_source")
        if source != last_source:
            chunk_index = 0
            last_source = source
        # A more robust ID might include a hash of the content to detect changes
        # For now, source:chunk_index is sufficient given the context.
        chunk_id = f"{source}:{chunk_index}"
        chunk.metadata["id"] = chunk_id
        chunk_index += 1
    return chunks


# Turning the data dictionary to a list of Langchain Documents
def generate_docs(processed_data: dict):
    """
    Converts a dictionary of processed data (link -> text content) into
    a list of LangChain Document objects.
    """
    documents = []
    if not processed_data:
        print("Warning: No processed data provided to generate_docs.")
        return documents
    print(f"Generating LangChain Documents from {len(processed_data)} processed entries...")
    for link, text_content in processed_data.items():
        doc = Document(page_content=text_content, metadata={"source": link})
        documents.append(doc)
    print(f"Generated {len(documents)} Document objects.")
    return documents


# Splits each document into chunks
def split_documents(documents: list[Document]):
    """
    Splits a list of LangChain Documents into smaller chunks using
    RecursiveCharacterTextSplitter.
    """
    text_splitter = RecursiveCharacterTextSplitter(# I used smaller chunk sizes because I'm going to pass the entirety of the pages content to the llm later
        chunk_size=550, # Use around 950 for longer context
        chunk_overlap=50, # Use around 100 if you use around 950 chunk size
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", ". ", " "], # Which seperators to split on
        keep_separator=False
    )
    print(f"Splitting {len(documents)} documents into chunks...")
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")
    return chunks

# Stuff to allow me to clear the database (don't really understand this part, this is just what stackoverflow said)
def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree. Changes file permissions to allow deletion.
    """
    try:
        os.chmod(path, stat.S_IWRITE) # Ensure write permission
        func(path)
    except Exception as e:
        print(f"Error removing {path}: {e}")

# Clears the entire ChromaDB directory
def clear_database():
    """
    Deletes the entire ChromaDB persistence directory.
    """
    if os.path.exists(CHROMADATAPATH):
        print(f"Attempting to clear Chroma DB at: {CHROMADATAPATH}")
        try:
            shutil.rmtree(CHROMADATAPATH, onerror=on_rm_error)
            print("✅ Chroma DB cleared successfully.")
        except Exception as e:
            print(f"Failed to clear Chroma DB: {e}")
    else:
        print("Chroma DB directory not found, nothing to clear.")

def load_markdown_files_from_directory(directory_path: str) -> List[Tuple[str, str]]:
    """
    Loads all markdown files from a specified directory, including subdirectories.

    Args:
        directory_path (str): The path to the directory containing markdown files.

    Returns:
        List[tuple[str, str]]: A list of tuples, where each tuple contains
                                (file_name_relative_path, markdown_content).
                                The file_name_relative_path is relative to the directory_path.
    """
    markdown_files = []
    if not os.path.exists(directory_path):
        print(f"Warning: Directory not found: {directory_path}. Skipping markdown loading.")
        return markdown_files

    print(f"Loading markdown files from: {directory_path}...")
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith(".md"):
                file_path = os.path.join(root, file_name)
                # Get the path relative to the base directory for source metadata
                relative_path = os.path.relpath(file_path, directory_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    markdown_files.append((relative_path, content))
                except Exception as e:
                    print(f"❌ Error reading {file_path}: {e}")
    print(f"Loaded {len(markdown_files)} markdown files.")
    return markdown_files

# --- Retrieval Function (Conceptual) ---
def get_retriever(use_cloudify_collection: bool = False) -> Chroma:
    """
    Returns a ChromaDB client configured to retrieve from either the 'DTIAS'
    collection or the 'Cloudify' collection, based on the boolean flag.

    In a real application, if you need to search *both* collections,
    you would instantiate two Chroma clients and combine their search results
    or use a LangChain 'EnsembleRetriever' or 'ParentDocumentRetriever'.

    Args:
        use_cloudify_collection (bool): If True, returns a client for the 'Cloudify'
                                        collection. Otherwise, returns a client for 'DTIAS'.

    Returns:
        Chroma: A ChromaDB client instance for the specified collection.
    """
    collection_to_use = "Cloudify" if use_cloudify_collection else "DTIAS"
    print(f"Initializing retriever for collection: '{collection_to_use}'")
    db = Chroma(
        persist_directory=CHROMADATAPATH,
        embedding_function=get_embed_function(),
        collection_name=collection_to_use
    )
    return db


# --- Main Ingestion Logic ---
if __name__ == '__main__':

    CLEAR_DB_ON_START = False # Set to True to clear DB first
    DTIAS_INPUT_JSON_PATH = "ScrapingStuff/storedData/RagFormattedData.json" # Input file for DTIAS

    if CLEAR_DB_ON_START:
        clear_database()

    # --- Ingest DTIAS Documentation ---
    print("\n--- Ingesting DTIAS Documentation ---")
    print(f"Loading processed data from: {DTIAS_INPUT_JSON_PATH}")
    processed_data_dtias = {}
    try:
        with open(DTIAS_INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            processed_data_dtias = json.load(f)
        print(f"Loaded {len(processed_data_dtias)} entries for DTIAS.")
    except FileNotFoundError:
        print(f"❌ Error: DTIAS input file not found at {DTIAS_INPUT_JSON_PATH}. Skipping DTIAS ingestion.")
    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode JSON from {DTIAS_INPUT_JSON_PATH}. Skipping DTIAS ingestion.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during DTIAS loading: {e}. Skipping DTIAS ingestion.")

    if processed_data_dtias:
        all_docs_dtias = generate_docs(processed_data_dtias)
        if all_docs_dtias:
            chunks_dtias = split_documents(all_docs_dtias)
            if chunks_dtias:
                print("\nAdding DTIAS chunks to Chroma DB...")
                db_dtias = add_to_chroma(chunks_dtias, collection_name="DTIAS")
            else:
                print("No DTIAS chunks were created after splitting.")
        else:
            print("No DTIAS documents were generated.")
    else:
        print("No DTIAS data to process.")


    # --- Ingest Cloudify Documentation ---
    print("\n--- Ingesting Cloudify Documentation ---")

    all_cloudify_docs = []
    # Load all markdown files from the Cloudify directory
    cloudify_md_files = load_markdown_files_from_directory(CLOUDIFY_DOCS_DIR)

    if cloudify_md_files:
        for file_name, markdown_content in tqdm(cloudify_md_files, desc="Processing Cloudify MD files"):
            # Use the relative path for source_file in parse_markdown_for_contextual_chunks
            # and a general "Cloudify" base_source_name for the overall collection.
            cloudify_chunks = parse_markdown_for_contextual_chunks(markdown_content, file_name)
            docs_from_file = generate_docs_from_contextual_chunks(cloudify_chunks, "Cloudify_Docs")
            all_cloudify_docs.extend(docs_from_file) # Combine documents from all files

        if all_cloudify_docs:
            chunks_cloudify = split_documents(all_cloudify_docs)
            if chunks_cloudify:
                print("\nAdding Cloudify chunks to Chroma DB...")
                db_cloudify = add_to_chroma(chunks_cloudify, collection_name="Cloudify")
            else:
                print("No Cloudify chunks were created after splitting.")
        else:
            print("No Cloudify data to process after parsing files.")
    else:
        print("No Cloudify markdown files found to process.")


    print("\n--- Ingestion Script Finished ---")

    # --- Example of how to use the retriever (conceptual) ---
    print("\n--- Demonstrating Retrieval (Conceptual) ---")
    # To retrieve from DTIAS:
    dtias_retriever = get_retriever(use_cloudify_collection=False)
    # The get() method returns a dictionary, check its 'ids' key for count
    dtias_count = len(dtias_retriever.get(include=[])['ids'])
    print(f"DTIAS collection count: {dtias_count} documents.")

    # To retrieve from Cloudify:
    cloudify_retriever = get_retriever(use_cloudify_collection=True)
    cloudify_count = len(cloudify_retriever.get(include=[])['ids'])
    print(f"Cloudify collection count: {cloudify_count} documents.")

    # Example search (replace with actual query and handling)
    # query_text = "How do I list agents?"
    # print(f"\nSearching Cloudify collection for: '{query_text}'")
    # results = cloudify_retriever.similarity_search(query_text, k=3)
    # for res in results:
    #    print(f"   - Source: {res.metadata.get('source')}, Content: {res.page_content[:100]}...")

    # If you wanted to search both and combine results (example for a querying script):
    # This logic would typically live in a separate RAG pipeline or query handler.
    # combined_query_text = "How do I deploy an application?"
    # print(f"\nSearching DTIAS and Cloudify collections for: '{combined_query_text}'")
    # dtias_results = dtias_retriever.similarity_search(combined_query_text, k=3)
    # cloudify_results = cloudify_retriever.similarity_search(combined_query_text, k=3)
    # all_combined_results = dtias_results + cloudify_results
    # print(f"Combined search found {len(all_combined_results)} results (top 3 from each collection).")
    # # You'd typically sort or re-rank these combined results based on relevance score