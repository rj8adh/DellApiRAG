import chromadb
import os

# --- Configuration ---
CHROMADATAPATH = 'chromaDb' # Make sure this matches the path used by your main script

# --- Main Logic ---
def list_collections_new():
    if not os.path.exists(CHROMADATAPATH):
        print(f"Error: ChromaDB path '{CHROMADATAPATH}' does not exist.")
        print("Please ensure this script is in the correct directory or CHROMADATAPATH is set correctly.")
        return

    try:
        print(f"Attempting to connect to ChromaDB at: {CHROMADATAPATH}")
        # For ChromaDB 0.5.0+ use chromadb.PersistentClient
        client = chromadb.PersistentClient(path=CHROMADATAPATH)
        print("Successfully connected to ChromaDB client.")
    except Exception as e:
        print(f"Error connecting to ChromaDB client at '{CHROMADATAPATH}': {e}")
        return

    try:
        print("\nFetching list of collections...")
        collections_list = client.list_collections() # This returns a list of Collection objects

        if collections_list:
            for collection in collections_list:
                print(collection)
        else:
            print("No collections found in the database.")
    except Exception as e:
        print(f"Error listing collections: {e}")

if __name__ == "__main__":
    list_collections_new()