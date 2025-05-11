# streamlit_app.py

import streamlit as st
import time # Import the time module
import contextModel # Your RAG system model
import reframeQuery # Our new query reframing module

# Configuring page
st.set_page_config(page_title="Documentation Chatbot", layout="centered")
st.title("Documentation Chatbot")
st.caption("Ask me questions about the documentation!")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session state for the toggle button
if "use_query_reframing" not in st.session_state:
    st.session_state.use_query_reframing = True # Default to using reframing

# Add the toggle button to the sidebar
with st.sidebar:
    st.header("Settings")
    st.session_state.use_query_reframing = st.toggle(
        "Use Query Reframing",
        value=st.session_state.use_query_reframing,
        help="Turn this on to allow the system to rephrase your query based on chat history for better context. Turn it off to send the original query directly."
    )


# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("Sources Used"):
                for source in message["sources"]:
                    st.write(source) # Display each source
        # Display rephrased query info from history if available
        if "rephrased_query" in message and message["rephrased_query"]:
            st.caption(f"ℹ️ Query sent to RAG: \"{message['rephrased_query']}\"")
        # Display timer info from history if available
        if "time_to_first_token" in message and message["time_to_first_token"] is not None:
             st.caption(f"⏱️ Time to first token: {message['time_to_first_token']:.2f} seconds")


# Get input from the user
if user_prompt := st.chat_input("What is your question?"):
    # Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # --- Determine the final query based on the toggle state ---
    final_query_for_rag = user_prompt # Start with the original user prompt

    # Check if the reframe toggle is on
    if st.session_state.use_query_reframing:
        # Prepare chat history for reframing (all messages except the current user prompt)
        # The query reframer expects a list of dicts: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        chat_history_for_reframing = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages[:-1] # Exclude the current user_prompt
        ]

        # Reframe the user's prompt based on the chat history (NON-STREAMING call)
        try:
            rephrased_query = reframeQuery.reframe_query_with_history(
                query=user_prompt,
                chat_history=chat_history_for_reframing
            )
            # If the rephrased query is different, use it
            if rephrased_query != user_prompt:
                 final_query_for_rag = rephrased_query
                 print(f"DEBUG: Query rephrased from '{user_prompt}' to '{final_query_for_rag}'")
            else:
                print(f"DEBUG: Query reframing active, but rephrased query is same as original: '{user_prompt}'")

        except Exception as e:
            st.warning(f"Could not reframe query due to an error: {e}. Using original query.")
            final_query_for_rag = user_prompt # Fallback to original query
            print(f"DEBUG: Error during query reframing: {e}. Using original query.")

    else:
        # If reframing is off, the final query is simply the original prompt
        print(f"DEBUG: Query reframing is OFF. Using original query: '{user_prompt}'")

    # Note: The st.info message about rephrased query is removed here.
    # The "Query sent to RAG" caption will be added to the assistant message below
    # only if the query was actually rephrased when reframing was active.
    # --- End of Query Reframing Decision Step ---

    # Getting the chatbot response using the (potentially rephrased) query
    with st.chat_message("assistant"):
        message_placeholder = st.empty() # Placeholder for the streaming response
        sources_placeholder = st.empty() # Placeholder for the sources
        full_rag_response = ""
        rag_sources = []
        time_to_first_chunk = None # Initialize variable to store the timer result

        try:
            print(f"DEBUG: Calling contextModel.single_query with query: '{final_query_for_rag}'")

            # --- Start Timer ---
            # Record the time just before calling the RAG model function
            start_time_stream = time.time()
            # --- End Timer ---

            # Call the single_query function from your contextModel file
            # This part assumes contextModel.single_query returns a stream generator and sources
            response_stream, rag_sources = contextModel.single_query(final_query_for_rag, use_formatted_data=False)

            if response_stream:
                first_chunk_received = False
                # Manually iterate the stream to time the first chunk and display progressively
                for chunk in response_stream:
                    if not first_chunk_received:
                        # --- Stop Timer ---
                        # Record the time when the very first chunk is received
                        end_time_first_chunk = time.time()
                        time_to_first_chunk = end_time_first_chunk - start_time_stream
                        first_chunk_received = True
                        # --- End Timer ---

                    full_rag_response += chunk
                    # Update the placeholder with the accumulated response as chunks arrive
                    message_placeholder.markdown(full_rag_response)


                print(f"DEBUG: RAG Stream finished. Full response length: {len(full_rag_response)}")

                # Displaying sources after the stream is complete
                if rag_sources:
                    print(f"DEBUG: RAG Sources found: {rag_sources}")
                    with sources_placeholder.expander("Sources Used"):
                        for source in rag_sources:
                            st.write(source)
                else:
                    print("DEBUG: No RAG sources returned.")
                    sources_placeholder.empty() # Remove placeholder if no sources

                # --- Display Timer Result ---
                # Display the calculated time to the first chunk after the response is complete
                if time_to_first_chunk is not None:
                     st.caption(f"⏱️ Time to first token: {time_to_first_chunk:.2f} seconds")
                # --- End Display Timer Result ---

            else:
                # Handle the case where response_stream is None (e.g., an error occurred before streaming)
                error_message = "Sorry, I encountered an error trying to get a response from the RAG system (no stream received)."
                message_placeholder.markdown(error_message)
                full_rag_response = error_message
                print("DEBUG: contextModel.single_query returned None for response_stream.")


        except ImportError as ie:
            error_msg = f"Import Error: {ie}. Make sure 'contextModel.py' and its dependencies are accessible."
            st.error(error_msg)
            full_rag_response = "Error: Could not load RAG components."
            print(f"DEBUG: ImportError in Streamlit app: {ie}")
        except Exception as e:
            error_msg = f"An unexpected error occurred with the RAG system: {e}"
            st.error(error_msg)
            full_rag_response = "Sorry, I ran into a problem processing your request. Please try again."
            print(f"DEBUG: Exception during contextModel.single_query call: {e}")


    # Add assistant response and potentially timer info/rephrased query to chat history
    assistant_message_to_store = {"role": "assistant", "content": full_rag_response}

    # Add sources if available
    if rag_sources:
        assistant_message_to_store["sources"] = rag_sources

    # Add the rephrased query to the message history ONLY IF reframing was on AND it changed the query
    if st.session_state.use_query_reframing and final_query_for_rag != user_prompt:
        assistant_message_to_store["rephrased_query"] = final_query_for_rag

    # Store the time to first token if it was successfully measured
    if time_to_first_chunk is not None:
         assistant_message_to_store["time_to_first_token"] = time_to_first_chunk

    st.session_state.messages.append(assistant_message_to_store)