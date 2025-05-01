#TODO Figure out the streaming responses
import streamlit as st
import time 
import contextModel

# Configuring page
st.set_page_config(page_title="Documentation Chatbot", layout="centered")
st.title("Documentation Chatbot")
st.caption("Ask me questions about the documentation!")

# Streamlit session stuff to track message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Iterate through the stored messages and display them
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display message content
        st.markdown(message["content"])
        # Display sources if they exist for an assistant message
        if "sources" in message and message["sources"]:
            with st.expander("Sources Used"):
                for source in message["sources"]:
                    st.write(source) # Display each source on a new line

# Get input from the user via the chat input box at the bottom
if prompt := st.chat_input("What is your question?"):
    # Adding the user message to the chat history and displaying it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Getting the chatbot response
    with st.chat_message("assistant"):
        message_placeholder = st.empty() # Create a placeholder for the streaming response
        full_response = ""
        sources_placeholder = st.empty() # Create a placeholder for the sources

        try:
            # Call the single_query function from your contextModel file
            # It returns a stream generator and the list of sources
            print(f"DEBUG: Calling single_query with: '{prompt}'") # Add debug print
            response_stream, sources = contextModel.single_query(prompt, use_formatted_data=False) # Assuming default behavior for UI

            if response_stream:
                # Use st.write_stream to display the streamed response chunks
                full_response = st.write_stream(response_stream)
                print(f"DEBUG: Stream finished. Full response length: {len(full_response)}") # Add debug print

                # Displaying sources after the stream is complete
                if sources:
                    print(f"DEBUG: Sources found: {sources}")
                    with sources_placeholder.expander("Sources Used"):
                         for source in sources:
                             st.write(source)
                else:
                    print("DEBUG: No sources returned.")
                    sources_placeholder.empty() # Remove placeholder if no sources


            else:
                 # Handle cases where single_query might return None for the stream
                 error_message = "Sorry, I encountered an error trying to get a response."
                 message_placeholder.markdown(error_message)
                 full_response = error_message
                 sources = [] # Sources is an empty list on error
                 print("DEBUG: single_query returned None for response_stream.") # Add debug print


        except ImportError as ie:
             st.error(f"Import Error: {ie}. Make sure 'contextModel.py' and its dependencies (like 'embeddingsMain.py') are in the same directory or accessible in your Python path.")
             full_response = "Error: Could not load necessary components."
             sources = []
             print(f"DEBUG: ImportError: {ie}") # Add debug print
        except Exception as e:
            # Display a general error message if something goes wrong
            error_message = f"An error occurred: {e}"
            st.error(error_message)
            full_response = "Sorry, I ran into a problem. Please try again."
            sources = [] # Ensure sources is an empty list on error
            print(f"DEBUG: Exception during single_query call: {e}") # Add debug print


    # Adding stuff to history
    assistant_message = {"role": "assistant", "content": full_response}
    if sources:
        assistant_message["sources"] = sources
    st.session_state.messages.append(assistant_message)