import os
import streamlit as st
from dotenv import load_dotenv

from file_parser import process_uploaded_file
from api_client import get_agentrouter_client, fetch_available_models, prepare_messages_for_api
from config import SYSTEM_PRESETS, estimate_tokens, calculate_cost
from security_utils import redact_sensitive_data, scan_code_for_vulnerabilities
from data_utils import parse_csv_file, render_data_analysis_ui
from session_utils import export_chat_to_markdown, export_chat_to_json

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Multi-Modal AI Assistant & Security Auditor",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Multi-Modal AI Assistant & Security Auditor")
st.caption("Powered by AgentRouter API. Multi-model analysis, security auditing, multi-file inspection, and CSV chart visualization.")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

env_api_key = os.getenv("AGENTROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
env_base_url = os.getenv("AGENTROUTER_BASE_URL", "https://agentrouter.ai/v1")

api_key = st.sidebar.text_input(
    "AgentRouter API Key",
    value=env_api_key,
    type="password"
)

base_url = st.sidebar.text_input(
    "Base API URL",
    value=env_base_url
)

models_list = fetch_available_models(api_key, base_url)

mode = st.sidebar.radio("Mode", ["Standard Assistant Chat", "Side-by-Side Model Comparison"])

if mode == "Standard Assistant Chat":
    selected_model = st.sidebar.selectbox("Select Model", options=models_list, index=0)
    custom_model = st.sidebar.text_input("Or custom model name:", value="", key="custom_single")
    model_to_use = custom_model.strip() if custom_model.strip() else selected_model
else:
    st.sidebar.markdown("**Select Models for Comparison:**")
    model_a = st.sidebar.selectbox("Model A", options=models_list, index=0, key="model_a")
    model_b = st.sidebar.selectbox("Model B", options=models_list, index=min(1, len(models_list)-1), key="model_b")

# System Persona / Prompt Presets
selected_preset_name = st.sidebar.selectbox("Select System Persona Preset", list(SYSTEM_PRESETS.keys()), index=0)
system_prompt_text = st.sidebar.text_area("System Prompt", value=SYSTEM_PRESETS[selected_preset_name], height=100)

# Security & Data Toggles
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Security & Privacy Settings")
auto_redact_pii = st.sidebar.checkbox("Auto-Redact Credentials & PII prior to sending", value=True)
auto_security_scan = st.sidebar.checkbox("Run Static Vulnerability Scan on uploaded code", value=True)

# File Uploader
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Upload Files / Images / Documents / Data")
uploaded_files = st.sidebar.file_uploader(
    "Attach files (PDF, DOCX, TXT, CSV, PNG, JPG, etc.)",
    accept_multiple_files=True
)

parsed_attached_files = []
csv_datasets = []
security_scan_results = []

if uploaded_files:
    for uf in uploaded_files:
        ext = uf.name.split(".")[-1].lower() if "." in uf.name else ""

        if ext == "csv":
            csv_res = parse_csv_file(uf.getvalue(), uf.name)
            if csv_res["success"]:
                csv_datasets.append(csv_res)
                parsed_attached_files.append({
                    "filename": uf.name,
                    "file_type": "document",
                    "content": csv_res["summary_text"]
                })
        else:
            parsed_file = process_uploaded_file(uf)
            parsed_attached_files.append(parsed_file)

            if parsed_file["file_type"] == "image":
                st.sidebar.image(parsed_file["content"], caption=parsed_file["filename"], use_container_width=True)
            elif parsed_file["file_type"] == "document" and auto_security_scan:
                scan_res = scan_code_for_vulnerabilities(parsed_file["content"], parsed_file["filename"])
                if scan_res:
                    security_scan_results.extend(scan_res)

if security_scan_results:
    st.warning("⚠️ **Static Security Findings in uploaded code:**")
    for warn in security_scan_results:
        st.write(warn)

# CSV Data Visualization Section
if csv_datasets:
    for ds in csv_datasets:
        render_data_analysis_ui(ds["df"], ds["filename"])
    st.markdown("---")

# Session State Initializations
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens_used" not in st.session_state:
    st.session_state.total_tokens_used = 0
if "estimated_cost" not in st.session_state:
    st.session_state.estimated_cost = 0.0

# Export & Session Management
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Chat History Management")
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.session_state.total_tokens_used = 0
    st.session_state.estimated_cost = 0.0
    st.rerun()

if st.session_state.messages:
    md_export = export_chat_to_markdown(st.session_state.messages)
    json_export = export_chat_to_json(st.session_state.messages)
    st.sidebar.download_button("📥 Export Chat as Markdown", md_export, file_name="chat_history.md", mime="text/markdown")
    st.sidebar.download_button("📥 Export Chat as JSON", json_export, file_name="chat_history.json", mime="application/json")

st.sidebar.metric("Total Estimated Tokens", st.session_state.total_tokens_used)
st.sidebar.metric("Total Estimated Cost ($)", f"${st.session_state.estimated_cost:.5f}")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Chat Input
if prompt := st.chat_input("Ask a question, analyze security, inspect documents, or compare models..."):
    if not api_key:
        st.error("Please enter your AgentRouter API key in the sidebar or set AGENTROUTER_API_KEY environment variable.")
    else:
        # PII Redaction
        prompt_to_send = prompt
        if auto_redact_pii:
            prompt_to_send, r_count = redact_sensitive_data(prompt)
            if r_count > 0:
                st.info(f"🛡️ Auto-redacted {r_count} sensitive token(s)/credential(s) from user prompt.")

        # Render User Prompt
        with st.chat_message("user"):
            st.markdown(prompt_to_send)

        st.session_state.messages.append({"role": "user", "content": prompt_to_send})

        # Apply system prompt if given
        history_to_send = st.session_state.messages[:-1]
        if system_prompt_text.strip():
            history_to_send = [{"role": "system", "content": system_prompt_text.strip()}] + history_to_send

        # Process Attached Files with PII Redaction if requested
        processed_files = []
        for pf in parsed_attached_files:
            file_copy = dict(pf)
            if auto_redact_pii and file_copy["file_type"] == "document":
                file_copy["content"], _ = redact_sensitive_data(file_copy["content"])
            processed_files.append(file_copy)

        api_messages = prepare_messages_for_api(
            chat_history=history_to_send,
            attached_files=processed_files,
            user_prompt=prompt_to_send
        )

        in_tokens = estimate_tokens(str(api_messages))

        if mode == "Standard Assistant Chat":
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_resp = ""
                try:
                    client = get_agentrouter_client(api_key, base_url)
                    response = client.chat.completions.create(
                        model=model_to_use,
                        messages=api_messages,
                        stream=True
                    )
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            c = chunk.choices[0].delta.content
                            full_resp += c
                            placeholder.markdown(full_resp + "▌")
                    placeholder.markdown(full_resp)
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})

                    out_tokens = estimate_tokens(full_resp)
                    cost = calculate_cost(model_to_use, in_tokens, out_tokens)
                    st.session_state.total_tokens_used += (in_tokens + out_tokens)
                    st.session_state.estimated_cost += cost

                except Exception as e:
                    st.error(f"Error from AgentRouter API: {str(e)}")

        else: # Side-by-Side Model Comparison
            col_a, col_b = st.columns(2)
            resp_a_text = ""
            resp_b_text = ""

            with col_a:
                st.subheader(f"🤖 {model_a}")
                ph_a = st.empty()
                try:
                    client = get_agentrouter_client(api_key, base_url)
                    resp_a = client.chat.completions.create(model=model_a, messages=api_messages, stream=True)
                    for chunk in resp_a:
                        if chunk.choices and chunk.choices[0].delta.content:
                            c = chunk.choices[0].delta.content
                            resp_a_text += c
                            ph_a.markdown(resp_a_text + "▌")
                    ph_a.markdown(resp_a_text)
                except Exception as e:
                    st.error(f"Error ({model_a}): {str(e)}")

            with col_b:
                st.subheader(f"🤖 {model_b}")
                ph_b = st.empty()
                try:
                    client = get_agentrouter_client(api_key, base_url)
                    resp_b = client.chat.completions.create(model=model_b, messages=api_messages, stream=True)
                    for chunk in resp_b:
                        if chunk.choices and chunk.choices[0].delta.content:
                            c = chunk.choices[0].delta.content
                            resp_b_text += c
                            ph_b.markdown(resp_b_text + "▌")
                    ph_b.markdown(resp_b_text)
                except Exception as e:
                    st.error(f"Error ({model_b}): {str(e)}")

            combined_resp = f"**[{model_a} Response]:**\n{resp_a_text}\n\n---\n\n**[{model_b} Response]:**\n{resp_b_text}"
            st.session_state.messages.append({"role": "assistant", "content": combined_resp})

            out_tokens = estimate_tokens(resp_a_text + resp_b_text)
            cost_a = calculate_cost(model_a, in_tokens, estimate_tokens(resp_a_text))
            cost_b = calculate_cost(model_b, in_tokens, estimate_tokens(resp_b_text))
            st.session_state.total_tokens_used += (in_tokens * 2 + out_tokens)
            st.session_state.estimated_cost += (cost_a + cost_b)
