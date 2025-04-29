from langchain_chroma import Chroma

def get_embed_function():
    return OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=API_KEY)

def add_to_chroma(chunks: list[Document]):
    db = Chroma(
        persist_directory=CHROMADATAPATH,
        embedding_function=get_embed_function()
    )

    chunks_with_ids = calculate_chunk_ids(chunks)

    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        print(f"👉 Adding new documents: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
    else:
        print("✅ No new documents to add")
    print("Storing chunk:", chunk.page_content[:2000], "...")
    return db

def calculate_chunk_ids(chunks):
    # Grouping chunks by source
    source_chunks = {}
    for chunk in chunks:
        source = chunk.metadata.get("source")
        if source not in source_chunks:
            source_chunks[source] = []
        source_chunks[source].append(chunk)
    
    # For each source, assign sequential IDs with page numbers included
    for source, source_chunks_list in source_chunks.items():
        # Sort chunks by page number first
        source_chunks_list.sort(key=lambda x: x.metadata.get("page", 0))
        
        last_page = None
        chunk_index = 0
        
        for chunk in source_chunks_list:
            page = chunk.metadata.get("page", 0)
            
            # Reset chunk index when page changes
            if page != last_page:
                chunk_index = 0
                last_page = page
            
            # Creating unique id for each chunk based on the source text, the page number, and the chunk index
            chunk_id = f"{source}:{page}:{chunk_index}"
            chunk.metadata["id"] = chunk_id
            
            chunk_index += 1
    
    return chunks

def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clear_database():
    if os.path.exists(CHROMADATAPATH):
        shutil.rmtree(CHROMADATAPATH, onerror=on_rm_error)
        print("✅ Chroma DB cleared.")
    else:
        print("Chroma DB not found.")

if __name__ == '__main__':
    # clear_database()
    allTextbooks = load_documents('data')
    chunks = split_documents(allTextbooks)
    print(chunks[0])
    add_to_chroma(chunks)

# Testing chunks
# if __name__ == '__main__':
#     # clear_database()

#     allTextbooks = load_documents('data')
#     chunks = split_documents(allTextbooks)

#     print(f"\n🔍 Total Chunks: {len(chunks)}\n")

#     for i, chunk in enumerate(chunks[20:]):
#         print(f"--- Chunk {i + 1} ---")
#         print(f"Source: {chunk.metadata.get('source')}")
#         print(f"Page: {chunk.metadata.get('page')}")
#         print(f"Content:\n{chunk.page_content}\n")
#         print("-" * 40)