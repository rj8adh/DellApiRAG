# query_reframer.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

# --- Enhanced Prompt Template with Few-Shot Examples ---
REPHRASE_PROMPT_TEMPLATE = """
You are an expert query analyzer. Your sole purpose is to rephrase a user's 'Original User Query' based on the 'Provided Chat History Context' *only when necessary* to make it fully standalone and suitable for a Retrieval Augmented Generation (RAG) system that does NOT have access to the prior conversation.

IMPORTANT INSTRUCTIONS:
1.  **FIRST AND FOREMOST: Preserve Standalone Queries (NO CHANGES):** Read the 'Original User Query'. If it is ALREADY a clear, specific, and fully self-contained question that makes sense on its own *without* needing *any* information from the 'Provided Chat History Context' to understand its core meaning, then you **MUST output the 'Original User Query' EXACTLY as it is, and STOP.** **DO NOT modify it in any way**, including changing terminology (e.g., 'config map' to 'configuration file'), adding extra phrases (e.g., 'from my system'), altering its structure, or replacing its subject with a subject from the history. This is your primary filter and the most important rule.
2.  **If Rephrasing IS Necessary (Query is Ambiguous):** ONLY if the 'Original User Query' is ambiguous or incomplete on its own (e.g., uses pronouns like "it", "them", "that", or is a follow-up question that lacks a clear subject), proceed to rephrase it.
3.  **How to Rephrase (Resolve Ambiguity):** When rephrasing (as determined in Instruction 2), integrate necessary context from the 'Provided Chat History Context' to form a complete, unambiguous question.
    * Resolve pronouns and vague references to the main nouns/entities discussed *in the history* that the 'Original User Query' is referring to.
    * **Subject Precedence:** If the 'Original User Query' contains a specific subject noun (e.g., "config map", "user account", "blueprint"), this subject takes precedence. Only replace or augment this subject with context from history if the user's query subject is clearly a pronoun referring to a historical subject, or if the history provides a necessary clarifying detail about *that specific subject* mentioned in the current query. **NEVER** replace a clear subject in the 'Original User Query' with a different subject from the history.
4.  **Strictly Avoid Assistant's Specific Details from History:**
    * **NEVER** include specific technical details, **product names, system names** (like 'Dell Telecom Infrastructure Automation Suite repository'), specific API information (endpoints, request types like GET/POST/DELETE), specific parameters (e.g., 'Tenant', 'BlueprintId', 'Force'), specific response fields or formats (e.g., 'model apiprotoResponse'), code snippets, or detailed step-by-step instructions that came *only* from the *Assistant's previous responses*.
    * This rule is **CRITICAL**. The history is *only* for resolving ambiguity in the 'Original User Query' (as per Instruction 2), NOT for adding the Assistant's specific, potentially system-dependent details to the user's generic query. Do not assume the user is asking about the *specific system or method* the assistant previously described, but rather about the general *subject or action* in their current query. If the 'Original User Query' uses generic terms (e.g., 'blueprint', 'config map', 'user account'), the rephrased query should keep it generic, even if the history mentioned these items within a specific system context provided by the Assistant.
    * This rule is especially crucial when the user's 'Original User Query' is about a different subject or action than the one detailed in the Assistant's prior response, or is a generic query following a discussion involving specific system details.
    * **Exception:** Only include a specific detail from an *Assistant's* response if the 'Original User Query' directly references or asks *specifically about that particular detail* provided by the Assistant (e.g., "You mentioned the 'Force' parameter, what does it do?"). In such a rare case, the rephrased query should focus *only* on understanding that specific mentioned detail.
    * For example, if the history shows the assistant explaining how to *upload* something using a specific API *in Dell Telecom Infrastructure Automation Suite*, and the user then asks "how do I delete it?", the "it" refers to the *item* discussed (e.g., "blueprint"), not the specific API method or product suite. The rephrased query must be about deleting the *item*, ignoring the previous API upload details and the product suite name. This is covered in Example 6.
5.  **Output Format:** Your entire output MUST be ONLY the rephrased query itself. Do NOT include any conversational phrases, explanations, apologies, or any text before or after the rephrased query (e.g., do not output "Rephrased Query: ...").

--- EXAMPLES START ---

**Example 1: Context is needed (Follow-up question)**
Provided Chat History Context:
User: How do I find information about the 'Alpha Centauri' project?
Assistant: The 'Alpha Centauri' project documentation is on the internal Wiki under 'Projects/AlphaCentauri'. It includes the project goals, team members, and timelines.

Original User Query:
What are its key deliverables?

Rephrased Query:
What are the key deliverables for the 'Alpha Centauri' project?

---
**Example 2: Query is already standalone (Technical Terminology) - PRESERVE EXACTLY**
Provided Chat History Context:
User: I was reading about managing blueprints. How do I upload a design blueprint?
Assistant: You can upload a design blueprint using a POST request to the /v1/blueprints endpoint in the system API.
User: I also worked with config files earlier.
Assistant: Yes, the configuration files are located at /etc/...

Original User Query:
how do I delete a config map?

Rephrased Query:
how do I delete a config map?

---
**Example 3: Context is needed (Pronoun resolution and adding subject)**
Provided Chat History Context:
User: We talked about updating the client database schema.
Assistant: Yes, the proposed changes include adding a 'last_contacted_date' field and an 'engagement_score'.
User: Which team is responsible for implementing that?
Assistant: The 'Database Engineering' team will handle the schema update.

Original User Query:
When will they start working on it?

Rephrased Query:
When will the 'Database Engineering' team start working on implementing the client database schema update?

---
**Example 4: Context is needed (Implicit subject from conversation flow, avoiding assistant's specific method)**
Provided Chat History Context:
User: How do I get a list of all active user accounts?
Assistant: You can use the `get_active_users()` function in the admin SDK.
User: And how do I add a new one?
Assistant: To add a new user account, you would use the `create_user_account(details)` function, making sure to include 'username' and 'email'.

Original User Query:
Now, how do I disable it?

Rephrased Query:
How do I disable an active user account?

---
**Example 5: Query is already standalone (General knowledge)**
Provided Chat History Context:
User: I'm trying to configure the 'DataStreamer v3' application.
Assistant: Okay, to configure 'DataStreamer v3', you first need to open its configuration file located at /etc/datastreamer/config.xml. Then, you'll want to set the 'source_topic' and 'sink_topic' parameters.
User: Got it. What about setting up alerts for it?
Assistant: For alerts, 'DataStreamer v3' integrates with 'AlertManager'. You'd define rules in 'AlertManager' based on metrics from 'DataStreamer v3'.

Original User Query:
What is the capital of France?

Rephrased Query:
What is the capital of France?

---
**Example 6: Context is needed (Focus on ITEM, not assistant's previous API details or product name for a DIFFERENT action)**
Provided Chat History Context:
User: How can I upload a new design blueprint to the system using the Dell Telecom Infrastructure Automation Suite API?
Assistant: You can upload a new design blueprint using its ID via a POST request to the /v1/tenants/{{Tenant}}/blueprints/{{BlueprintId}} API operation in Dell Telecom Infrastructure Automation Suite. Ensure all required fields like 'name' and 'description' are correctly filled out.
User: Thanks, that's clear.

Original User Query:
Now how do I delete one?

Rephrased Query:
How do I delete an uploaded blueprint?

---
**Example 7: Context needed, but ABSOLUTELY avoid assistant's technical details, product name, etc., from previous, different action**
Provided Chat History Context:
User: How to delete a blueprint in Dell Telecom Infrastructure Automation Suite?
Assistant: To delete a blueprint in Dell Telecom Infrastructure Automation Suite, send a DELETE request to /v1/blueprints/{{BlueprintId}}. You can optionally include the 'force' parameter for extra privileges. The successful response contains 'Tenant', 'BlueprintId', and indicates model 'apiprotoResponse'.
User: Okay, got it about deletion.

Original User Query:
how do I upload one?

Rephrased Query:
How to upload a blueprint?

---
**Example 8: Avoid product/system name from history for a generic "retrieve" query**
Provided Chat History Context:
User: I need to work with blueprints. Where are they stored?
Assistant: Blueprints are stored in the repository within the Dell Telecom Infrastructure Automation Suite. You can access them via the /v1/blueprints endpoint.

Original User Query:
How can I retrieve one?

Rephrased Query:
How can I retrieve a blueprint?

--- EXAMPLES END ---

Now, apply these principles to the following:

Provided Chat History Context:
{chat_history}

---

Original User Query:
{query}
"""

# --- LLM Initialization ---
LLM = OllamaLLM(model='phi3:mini') # Ensure 'phi3:mini' is available

def format_chat_history_for_prompt(history: list[dict]) -> str:
    if not history:
        return "No prior conversation." # More explicit for the LLM
    formatted_history = []
    for message in history:
        role = message.get('role', 'unknown').capitalize()
        content = message.get('content', '')
        formatted_history.append(f"{role}: {content}")
    return "\n".join(formatted_history)

def reframe_query_with_history(query: str, chat_history: list[dict]) -> str:
    print(f"Original query for reframing: \"{query}\"")
    
    formatted_history_str = format_chat_history_for_prompt(chat_history)
    
    prompt_template = ChatPromptTemplate.from_template(REPHRASE_PROMPT_TEMPLATE)
    prompt_with_values = prompt_template.format(chat_history=formatted_history_str, query=query)
    
    print(f"\n--- Sending this to LLM for Reframing (Full Prompt) ---")
    print(prompt_with_values) # Crucial for debugging
    print("--- End of Reframing Prompt ---\n")

    try:
        response = LLM.invoke(prompt_with_values)
        rephrased_query = response.strip() # Strip whitespace
        
        # Additional check: Sometimes models might still output the "Rephrased Query:" prefix despite instructions.
        # This is a fallback, ideally the prompt handles it.
        if rephrased_query.lower().startswith("rephrased query:"):
            rephrased_query = rephrased_query.split(":", 1)[1].strip()
            
        print(f"✅ LLM rephrased query: \"{rephrased_query}\"")
        return rephrased_query
    except Exception as e:
        print(f"❌ Error invoking LLM for reframing: {e}")
        print("⚠️ Returning original query due to reframing error.")
        return query

if __name__ == '__main__':
    print("--- Running Test Cases for Query Reframer ---")

    test_cases = [
        {
            "name": "Test Case 1: Query needs context (Follow-up)",
            "history": [
                {"role": "user", "content": "How do I get all the service tags for my devices?"},
                {"role": "assistant", "content": "You can retrieve service tags using the API endpoint /devices/servicetags."}
            ],
            "query": "Now, how can I upload them to the new portal?",
            "expected_partial": "upload service tags to the new portal"
        },
        {
            "name": "Test Case 2: Query is self-contained",
            "history": [
                {"role": "user", "content": "What's the weather like today?"},
                {"role": "assistant", "content": "It's sunny with a high of 75°F."}
            ],
            "query": "How do I reset my password for the company portal?",
            "expected_partial": "How do I reset my password for the company portal?"
        },
        {
            "name": "Test Case 3: RAG-style context (Pronoun)",
            "history": [
                {"role": "user", "content": "I'm looking for information on the 'Blue-sky' project."},
                {"role": "assistant", "content": "The 'Blue-sky' project aims to develop next-generation solar panels. Key documents include the project charter and the Q1 progress report."},
                {"role": "user", "content": "Where can I find the Q1 progress report?"},
                {"role": "assistant", "content": "The Q1 progress report for the 'Blue-sky' project is located in the shared drive under /projects/blue-sky/reports/Q1_Progress.pdf."},
            ],
            "query": "What are the main risks outlined in it?",
            "expected_partial": "risks outlined in the Q1 progress report for the 'Blue-sky' project"
        },
        {
            "name": "Test Case 4: Empty history",
            "history": [],
            "query": "How to install Python?",
            "expected_partial": "How to install Python?"
        },
        {
            "name": "Test Case 5: Simple pronoun",
            "history": [
                {"role": "user", "content": "The new XZ-500 printer is causing issues."},
                {"role": "assistant", "content": "Okay, what kind of issues are you seeing with the XZ-500 printer?"}
            ],
            "query": "How do I restart it?",
            "expected_partial": "restart the XZ-500 printer"
        },
        {
            "name": "Test Case 6: Blueprint Scenario (Crucial Test)",
            "history": [
                {"role": "user", "content": "How can I upload a new blueprint to the system?"},
                {"role": "assistant", "content": "You can upload a new blueprint using its ID via a POST request to the /v1/tenants/{Tenant}/blueprints/{BlueprintId} API operation. Ensure all required fields like 'name' and 'description' are correctly filled out before making the request."},
                {"role": "user", "content": "Thanks, that worked!"} # Added a user confirmation for realism
            ],
            "query": "Now how do I delete one?",
            "expected_partial": "delete an uploaded blueprint" # Or "delete a design blueprint"
        },
        {
            "name": "Test Case 7: Similar to blueprint but different subject",
            "history": [
                {"role": "user", "content": "How do I submit a support ticket for a software bug?"},
                {"role": "assistant", "content": "You can submit a support ticket via our online portal at support.example.com/tickets/new. Please include the software version and steps to reproduce the bug."},
            ],
            "query": "And how do I track its status?",
            "expected_partial": "track the status of a support ticket" # or "track its status for a software bug"
        }
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        rephrased = reframe_query_with_history(query=test["query"], chat_history=test["history"])
        print(f"Original: \"{test['query']}\"")
        print(f"Rephrased: \"{rephrased}\"")
        if test["expected_partial"].lower() in rephrased.lower():
            print(f"✅ Test Passed (Expected partial match: '{test['expected_partial']}')")
        else:
            print(f"⚠️ Test Potentially Failed (Expected partial match: '{test['expected_partial']}', Got: '{rephrased}')")
            
    print("\n--- End of Query Reframer Test Cases ---")