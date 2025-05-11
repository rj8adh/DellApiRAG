from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema.document import Document
import torch
import os
import shutil
import stat
import json
import re # <-- re was imported but not used, can be kept or removed
from tqdm import tqdm # <-- Import tqdm for progress bars

# Check PyTorch version and CUDA availability
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

# device = "cuda" if torch.cuda.is_available() else "cpu"
device = "cpu" # Force CPU as per original code
print(f"Using device: {device}") # Confirm which device is used

# Random constants (mostly configuration)
CHROMADATAPATH = 'chromaDb' # Path for the Chroma database
model_name = "Alibaba-NLP/gte-Qwen2-1.5B-instruct" # Embedding model
model_kwargs = {'device': device, 'trust_remote_code': True}
encode_kwargs = {'normalize_embeddings': False}

# Batching is just for the progress bar so I know how close I am to finishing
CHROMA_ADD_BATCH_SIZE = 64

# Embedding Function
def get_embed_function():
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

# Adding stuff the chroma database (also has progress bar)
def add_to_chroma(chunks: list[Document]):

    # Setting up the database connection
    db = Chroma(
        persist_directory=CHROMADATAPATH,
        embedding_function=get_embed_function()
    )

    # Ensure chunks have unique IDs before checking existing ones
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Checking existing documents
    try:
        existing_items = db.get(include=[])
        existing_ids = set(existing_items["ids"])
        print(f"Number of existing documents in DB: {len(existing_ids)}")
    except Exception as e:
        print(f"Warning: Could not get existing items, assuming DB is empty or needs rebuild: {e}")
        existing_ids = set()

    # Getting new chunks ready
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata.get("id") not in existing_ids:
            new_chunks.append(chunk)

    # Addding the new chunks to the database
    if len(new_chunks):
        print(f"Adding {len(new_chunks)} new documents in batches of {CHROMA_ADD_BATCH_SIZE}...")

        # Using tqdm for the progress bar over batches (i is the batches of chunks)
        for i in tqdm(range(0, len(new_chunks), CHROMA_ADD_BATCH_SIZE), desc="Adding to ChromaDB"):
            # Get the current batch of chunks
            batch = new_chunks[i:i + CHROMA_ADD_BATCH_SIZE]
            if not batch: # Should not happen with range logic, but safety check
                continue

            # Get the corresponding IDs for this batch
            batch_ids = [chunk.metadata["id"] for chunk in batch]

            # Add the current batch to ChromaDB
            # Embedding happens inside this call for the batch
            try:
                db.add_documents(batch, ids=batch_ids)
            except Exception as e:
                 print(f"\nError adding batch starting at index {i} to ChromaDB: {e}")

        print("✅ New documents added successfully.")

    else:
        # No new documents found
        print("✅ No new documents to add.")

    return db # Return the database client


# Calculates and assigns unique chunk ids
def calculate_chunk_ids(chunks: list[Document]):

    last_source = None
    chunk_index = 0
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown_source")
        if source != last_source:
            chunk_index = 0
            last_source = source
        chunk_id = f"{source}:{chunk_index}"
        chunk.metadata["id"] = chunk_id
        chunk_index += 1
    return chunks


# Turning the data dictionary to a list of Langchain Documents
def generate_docs(processed_data: dict):
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

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=514, # Use around 950 for longer context
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
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"Error removing {path}: {e}")

# Clears the current chromaDb
def clear_database():
    if os.path.exists(CHROMADATAPATH):
        print(f"Attempting to clear Chroma DB at: {CHROMADATAPATH}")
        try:
            shutil.rmtree(CHROMADATAPATH, onerror=on_rm_error)
            print("✅ Chroma DB cleared successfully.")
        except Exception as e:
            print(f"Failed to clear Chroma DB: {e}")
    else:
        print("Chroma DB directory not found, nothing to clear.")


# Main testing stuff
if __name__ == '__main__':

    CLEAR_DB_ON_START = True # Set to True to clear DB first
    INPUT_JSON_PATH = "ScrapingStuff/storedData/RagFormattedData.json" # Input file

    if CLEAR_DB_ON_START:
        clear_database()

    # Loading data
    print(f"Loading processed data from: {INPUT_JSON_PATH}")
    try:
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            processed_data_dict = json.load(f)
        print(f"Loaded {len(processed_data_dict)} entries.")
    # Extra error handling for debugging
    except FileNotFoundError:
        print(f"❌ Error: Input file not found at {INPUT_JSON_PATH}")
        exit()
    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode JSON from {INPUT_JSON_PATH}")
        exit()
    except Exception as e:
         print(f"❌ An unexpected error occurred during loading: {e}")
         exit()

    if not isinstance(processed_data_dict, dict) or not processed_data_dict:
        print(f"❌ Error: Input data is not a valid non-empty dictionary. Exiting.")
        exit()

    # Generating all the langchain documents
    all_docs = generate_docs(processed_data_dict)
    if not all_docs:
         print("No documents were generated. Exiting.")
         exit()

    # Chunking the documents
    chunks = split_documents(all_docs)
    if not chunks:
        print("No chunks were created after splitting. Exiting.")
        exit()

    # Adding and vectorizing the chunks to the chromadb
    print("\nAdding chunks to Chroma DB...")
    db_instance = add_to_chroma(chunks) # Has a cool progress bar now 😎

    print("\n--- Script Finished ---")