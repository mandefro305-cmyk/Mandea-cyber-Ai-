import os
import streamlit as st
from dotenv import load_dotenv

from file_parser import process_uploaded_file
from api_client import get_agentrouter_client, fetch_available_models, prepare_messages_for_api

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Multi-Modal AI Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Multi-Modal AI Assistant")
st.caption("Powered by AgentRouter API. Upload documents, images, and ask questions across models.")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

# API Key & Base URL Resolution
env_api_key = os.getenv("AGENTROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
env_base_url = os.getenv("AGENTROUTER_BASE_URL", "https://agentrouter.ai/v1")

api_key = st.sidebar.text_input(
    "AgentRouter API Key",
    value=env_api_key,
    type="password",
    help="Provided automatically via environment variable if configured, or enter manually."
)

base_url = st.sidebar.text_input(
    "Base API URL",
    value=env_base_url,
    help="The base endpoint for AgentRouter/OpenRouter API."
)

# Fetch models list
models_list = fetch_available_models(api_key, base_url)
selected_model = st.sidebar.selectbox(
    "Select Model",
    options=models_list,
    index=0
)

# Option to add custom model name
custom_model = st.sidebar.text_input("Or type custom model name:", value="")
if custom_model.strip():
    model_to_use = custom_model.strip()
else:
    model_to_use = selected_model

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Upload Files / Images / Documents")
uploaded_files = st.sidebar.file_uploader(
    "Attach files (PDF, DOCX, TXT, PNG, JPG, CSV, etc.)",
    accept_multiple_files=True,
    type=None
)

parsed_attached_files = []
if uploaded_files:
    for uf in uploaded_files:
        parsed_file = process_uploaded_file(uf)
        parsed_attached_files.append(parsed_file)
        if parsed_file["file_type"] == "image":
            st.sidebar.image(parsed_file["content"], caption=parsed_file["filename"], use_container_width=True)
        else:
            st.sidebar.success(f"📄 Loaded document: {parsed_file['filename']}")

# Initialize Chat Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Prompt
if prompt := st.chat_input("Ask a question, analyze documents, or process images..."):
    if not api_key:
        st.error("Please enter your AgentRouter API key in the sidebar or set the AGENTROUTER_API_KEY environment variable.")
    else:
        # Render user prompt in chat
        with st.chat_message("user"):
            st.markdown(prompt)
            if parsed_attached_files:
                for f in parsed_attached_files:
                    st.caption(f"📎 Attached: {f['filename']}")

        # Build payload
        api_messages = prepare_messages_for_api(
            chat_history=st.session_state.messages,
            attached_files=parsed_attached_files,
            user_prompt=prompt
        )

        # Record prompt in history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Request completion from AgentRouter API
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                client = get_agentrouter_client(api_key, base_url)
                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=api_messages,
                    stream=True
                )

                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        full_response += content_chunk
                        message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Error communicating with AgentRouter API: {str(e)}")
