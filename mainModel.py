from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from embeddingsMain import get_embed_function
from pprint import pprint
import argparse

CHROMADATAPATH = 'chromaDb'
PROMPT = """
You are an AI Documentation Chatbot. Answer the question a user just asked you BASED ONLY ON THE FOLLOWING CONTEXT:

{context}

---

Answer the question based on the above context: {question}
"""

MODEL = OllamaLLM(model="phi4-mini")

def single_query(query_text: str):
    # Preparing the database
    embedding_function = get_embed_function()
    db = Chroma(persist_directory=CHROMADATAPATH, embedding_function=embedding_function)

    # Searching the data
    results = db.similarity_search_with_score(query_text, k=5) # Gets the top 5 most relevant pieces of data

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print(prompt)

    response_text = MODEL.invoke(prompt)

    sources = [doc.metadata.get("id", None) for doc, _score in results]
    
    formatted_response = f"Response: {response_text}\n"
    print(formatted_response)
    pprint(f"Sources: {sources}\n")
    return response_text

def main():
    # The argparse stuff is just so you can run it in console with a string parameter
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    single_query(query_text)

if __name__ == "__main__":
    main()