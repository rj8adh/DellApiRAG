# query_reframer.py

import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM

# --- Refined Prompt Template for Minimal Query Reframing ---
REPHRASE_PROMPT_TEMPLATE = """
You are a Dell API documentation chatbot assistant. Your job is to make minimal adjustments to user queries for better context retrieval.

RULES:
1. Keep changes MINIMAL - only add necessary context from chat history
2. Preserve the original technical terms exactly as written
3. Do NOT add extra descriptive words like "design", "architectural", etc.
4. Focus on making the query standalone if it references previous context
5. If the query is already clear, keep it unchanged
6. You are an API Documentation chatbot, so a lot of the data you have uses terms such as "get", "post", etc. If the user uses a term along these lines, please keep it
Generate a JSON object with two keys:
- "reframed_query": The minimally adjusted query (or original if no changes needed)
- "embedding_text": Key technical terms for search (usually 2-4 words)

--- EXAMPLES ---

**Example 1:**
Chat History: No prior conversation.
User Query: how do I upload a blueprint
JSON Output:
{{
  "reframed_query": "how do I upload a blueprint",
  "embedding_text": "upload blueprint"
}}

**Example 2:**
Chat History:
User: How can I upload a blueprint?
Assistant: You can upload a blueprint using a POST request...
User Query: how do I delete it?
JSON Output:
{{
  "reframed_query": "how do I delete a blueprint",
  "embedding_text": "delete blueprint"
}}

**Example 3:**
Chat History: No prior conversation.
User Query: What is a blueprint?
JSON Output:
{{
  "reframed_query": "What is a blueprint?",
  "embedding_text": "blueprint definition"
}}

**Example 4 (Keep in mind instruction #6 for this one):**
Chat History:
User: How do I create a user account?
Assistant: You can create a user account by sending a POST request...
User Query: Now how do I get all of them?
JSON Output:
{{
  "reframed_query": "How to get all user accounts?",
  "embedding_text": "get user accounts"
}}

--- END EXAMPLES ---

**Chat History:**
{chat_history}

**User Query:**
{query}

**JSON Output:**
"""

# --- LLM Initialization ---
LLM = OllamaLLM(model='phi3:mini', format='json')

def format_chat_history_for_prompt(history: list[dict]) -> str:
    """Formats chat history into a simple, readable string for the prompt."""
    if not history:
        return "No prior conversation."
    formatted_history = []
    for message in history[-4:]:  # Only use last 4 messages for context
        role = message.get('role', 'unknown').capitalize()
        content = message.get('content', '')
        formatted_history.append(f"{role}: {content}")
    return "\n".join(formatted_history)

def reframe_query_with_history(query: str, chat_history: list[dict]) -> tuple[str, str]:
    """
    Reframes a query based on chat history with minimal changes.

    Args:
        query: The original user query.
        chat_history: A list of previous conversation messages.

    Returns:
        A tuple containing:
        - reframed_query (str): The minimally adjusted query.
        - embedding_text (str): The concise phrase for vector embedding.
    """
    print(f"Original query for reframing: \"{query}\"")
    
    formatted_history_str = format_chat_history_for_prompt(chat_history)
    
    prompt_template = ChatPromptTemplate.from_template(REPHRASE_PROMPT_TEMPLATE)
    
    # Using LangChain Expression Language (LCEL) to chain components
    chain = prompt_template | LLM | StrOutputParser()
    
    try:
        response_str = chain.invoke({
            "chat_history": formatted_history_str,
            "query": query
        })
        
        print(f"Raw LLM Output:\n{response_str}")
        
        # Parse the JSON output from the model
        response_json = json.loads(response_str)
        
        reframed_query = response_json.get("reframed_query")
        embedding_text = response_json.get("embedding_text")
        
        # Validate that both keys were found and have content
        if not all([reframed_query, embedding_text]):
            raise KeyError("One or both required keys ('reframed_query', 'embedding_text') are missing in the LLM response.")

        # Additional validation: if the reframed query is too different, fall back to original
        if len(reframed_query.split()) > len(query.split()) + 3:
            print(f"⚠️ Reframed query seems too verbose, using original query instead.")
            reframed_query = query

        print(f"✅ Reframed Query: \"{reframed_query}\"")
        print(f"✅ Embedding Text: \"{embedding_text}\"")
        
        return reframed_query, embedding_text
        
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"❌ Error processing LLM response for reframing: {e}")
        print("⚠️ Returning original query for both outputs due to an error.")
        # Fallback to the original query for both outputs to ensure the system doesn't fail
        return query, query

# --- Example Usage ---
if __name__ == '__main__':
    # Example 1: Context is needed
    print("--- Running Example 1: Context Needed ---")
    history_1 = [
        {'role': 'user', 'content': 'How can I upload a new design blueprint to the system?'},
        {'role': 'assistant', 'content': 'You can upload a new design blueprint using its ID via a POST request...'}
    ]
    query_1 = "now how do I upload one?"
    reframed_q, embedding_t = reframe_query_with_history(query_1, history_1)
    print("-" * 20)

    # Example 2: Query is already standalone
    print("\n--- Running Example 2: Standalone Query ---")
    history_2 = [
        {'role': 'user', 'content': 'I was reading about managing blueprints.'},
        {'role': 'assistant', 'content': 'Blueprints can be managed via the API.'}
    ]
    query_2 = "how do I delete a config map?"
    reframed_q, embedding_t = reframe_query_with_history(query_2, history_2)
    print("-" * 20)
    
    # Example 3: No History
    print("\n--- Running Example 3: No History ---")
    history_3 = []
    query_3 = "How to create a user account?"
    reframed_q, embedding_t = reframe_query_with_history(query_3, history_3)
    print("-" * 20)