import streamlit as st
import requests
import json

st.set_page_config(page_title="Sugar-AI Chat Interface", page_icon="🍬", layout="centered")
st.title("🍬 Sugar-AI Chat Interface")

# --- Sidebar: Auth + Endpoint Selection ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("API Key", type="password", placeholder="Enter your API key")
base_url = st.sidebar.text_input("Server URL", value="http://localhost:8000")

endpoint_choice = st.sidebar.selectbox(
    "Choose Endpoint",
    ["RAG (/ask)", "Direct LLM (/ask-llm)", "Custom Prompt (/ask-llm-prompted)", "Chat Mode (/ask-llm-prompted)"]
)

# --- Generation Parameters (only for custom/chat) ---
generation_params = {}
if endpoint_choice in ["Custom Prompt (/ask-llm-prompted)", "Chat Mode (/ask-llm-prompted)"]:
    with st.sidebar.expander("Generation Parameters", expanded=False):
        generation_params["max_length"] = st.number_input("Max Length", value=1024, min_value=100, max_value=2048)
        generation_params["temperature"] = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        generation_params["top_p"] = st.slider("Top P", 0.1, 1.0, 0.9, 0.1)
        generation_params["top_k"] = st.number_input("Top K", value=50, min_value=1, max_value=100)
        generation_params["repetition_penalty"] = st.slider("Repetition Penalty", 0.5, 2.0, 1.1, 0.1)
        generation_params["truncation"] = st.checkbox("Truncation", value=True)

# --- Chat history (for chat mode) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Main UI ---
st.subheader("Ask Sugar-AI")

if endpoint_choice == "Custom Prompt (/ask-llm-prompted)":
    custom_prompt = st.text_area(
        "Custom System Prompt",
        value="You are a helpful assistant for Sugar Labs. Provide clear, child-friendly answers.",
    )

if endpoint_choice == "Chat Mode (/ask-llm-prompted)":
    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful assistant for Sugar Labs.",
    )
    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Type your message...")
else:
    user_input = st.text_input("Enter your question:")

# --- Submit ---
submit = True if endpoint_choice == "Chat Mode (/ask-llm-prompted)" and user_input else False
if endpoint_choice != "Chat Mode (/ask-llm-prompted)":
    submit = st.button("Submit")

if submit or (endpoint_choice == "Chat Mode (/ask-llm-prompted)" and user_input):
    if not api_key:
        st.warning("Please enter an API key in the sidebar.")
    elif not user_input and endpoint_choice != "Chat Mode (/ask-llm-prompted)":
        st.warning("Please enter a question.")
    else:
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        try:
            response = None

            if endpoint_choice == "RAG (/ask)":
                response = requests.post(
                    f"{base_url}/ask",
                    params={"question": user_input},
                    headers={"X-API-Key": api_key},
                )

            elif endpoint_choice == "Direct LLM (/ask-llm)":
                response = requests.post(
                    f"{base_url}/ask-llm",
                    params={"question": user_input},
                    headers={"X-API-Key": api_key},
                )

            elif endpoint_choice == "Custom Prompt (/ask-llm-prompted)":
                payload = {
                    "question": user_input,
                    "custom_prompt": custom_prompt,
                    **generation_params,
                }
                response = requests.post(
                    f"{base_url}/ask-llm-prompted",
                    headers=headers,
                    data=json.dumps(payload),
                )

            elif endpoint_choice == "Chat Mode (/ask-llm-prompted)":
                # Build messages list
                if not st.session_state.messages:
                    st.session_state.messages.append({"role": "system", "content": system_prompt})
                st.session_state.messages.append({"role": "user", "content": user_input})

                payload = {
                    "chat": True,
                    "messages": st.session_state.messages,
                    **generation_params,
                }
                response = requests.post(
                    f"{base_url}/ask-llm-prompted",
                    headers=headers,
                    data=json.dumps(payload),
                )

            # --- Handle Response ---
            if response and response.status_code == 200:
                result = response.json()

                if endpoint_choice == "Chat Mode (/ask-llm-prompted)":
                    assistant_reply = result["choices"][0]["message"]["content"]
                    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    with st.chat_message("assistant"):
                        st.markdown(assistant_reply)
                else:
                    st.markdown("**Answer:**")
                    st.markdown(result.get("answer", "No answer returned."))

                # Sidebar stats
                if "user" in result:
                    st.sidebar.success(f"User: {result['user']}")
                if "quota" in result:
                    quota = result["quota"]
                    st.sidebar.info(f"Quota: {quota['remaining']}/{quota['total']} remaining")
                if "generation_params" in result and endpoint_choice in [
                    "Custom Prompt (/ask-llm-prompted)", "Chat Mode (/ask-llm-prompted)"
                ]:
                    with st.expander("Generation Parameters Used"):
                        st.json(result["generation_params"])

            elif response:
                if response.status_code == 401:
                    st.error("Invalid API key. Please check your credentials.")
                elif response.status_code == 429:
                    st.error("Daily quota exceeded. Try again tomorrow.")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to {base_url}. Make sure the server is running.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# --- Clear chat button for chat mode ---
if endpoint_choice == "Chat Mode (/ask-llm-prompted)" and st.session_state.messages:
    if st.sidebar.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
