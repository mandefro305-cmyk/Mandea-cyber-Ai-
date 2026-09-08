import os
import uuid
import streamlit as st
from dotenv import load_dotenv

from file_parser import process_uploaded_file
from api_client import get_agentrouter_client, fetch_available_models, prepare_messages_for_api
from config import SYSTEM_PRESETS, estimate_tokens, calculate_cost
from security_utils import redact_sensitive_data, scan_code_for_vulnerabilities
from ast_utils import analyze_python_ast
from data_utils import parse_csv_file, render_data_analysis_ui
from session_utils import export_chat_to_markdown, export_chat_to_json
from db_utils import init_db, create_session, get_all_sessions, save_message, get_session_messages, delete_session
from rag_utils import chunk_text, search_chunks
from remediation_utils import generate_remediation_diff
from search_utils import perform_web_search, format_search_context
from report_generator import generate_pdf_audit_report
from agent_engine import SecurityTaskPipeline
from auth_utils import register_user, authenticate_user

# Load environment variables & initialize DB
load_dotenv()
init_db()

st.set_page_config(
    page_title="Mâñđ€å Åî",
    page_icon="🤖",
    layout="wide"
)

# Custom ChatGPT-like styling with Theme Variable fallbacks
st.markdown("""
<style>
    /* Global Container Padding & Styling */
    .stApp {
        background-color: var(--background-color, #212121);
        color: var(--text-color, #ececec);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color, #171717);
        border-right: 1px solid #2f2f2f;
    }

    /* Main Header Styling */
    .chat-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
    }
    .chat-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #10a37f 0%, #34d399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .chat-subtitle {
        color: #b4b4b4;
        font-size: 0.95rem;
    }

    /* Suggestion Cards */
    .suggestion-card {
        background-color: #2f2f2f;
        border: 1px solid #424242;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        transition: transform 0.2s, border-color 0.2s;
    }
    .suggestion-card:hover {
        border-color: #10a37f;
    }
    .suggestion-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #f3f3f3;
        margin-bottom: 0.25rem;
    }
    .suggestion-desc {
        font-size: 0.82rem;
        color: #a0a0a0;
    }

    /* Input & Buttons */
    .stTextInput > div > div > input {
        border-radius: 8px;
        background-color: #2f2f2f;
        color: #ffffff;
        border: 1px solid #424242;
    }
    .stButton > button {
        border-radius: 8px;
        background-color: #10a37f;
        color: white;
        border: none;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #0e8e6f;
        color: white;
    }

    /* Chat Messages */
    div[data-testid="stChatMessage"] {
        background-color: transparent;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Authentication Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = "Guest"
if "user_role" not in st.session_state:
    st.session_state.user_role = "guest"

# User Auth Sidebar / Login Screen
st.sidebar.title("🔐 Authentication")
if not st.session_state.authenticated:
    auth_mode = st.sidebar.radio("Account", ["Login", "Register"])
    u_input = st.sidebar.text_input("Username")
    p_input = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.sidebar.button("Login"):
            success, msg, role = authenticate_user(u_input, p_input)
            if success:
                st.session_state.authenticated = True
                st.session_state.username = u_input
                st.session_state.user_role = role
                st.sidebar.success(f"Welcome back, {u_input}!")
                st.rerun()
            else:
                st.sidebar.error(msg)
    else:
        if st.sidebar.button("Register"):
            success, msg = register_user(u_input, p_input)
            if success:
                st.sidebar.success("Registration successful! You can now log in.")
            else:
                st.sidebar.error(msg)
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_role})")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = "Guest"
        st.session_state.user_role = "guest"
        st.rerun()

st.markdown("""
<div class="chat-header">
    <div class="chat-title">🤖 Mâñđ€å Åî</div>
    <div class="chat-subtitle">Powered by AgentRouter API. Multi-Modal Chat, AST Code Security Auditing, RAG & Multi-Agent Workflows</div>
</div>
""", unsafe_allow_html=True)

# Session State Initializations
if "current_session_id" not in st.session_state:
    new_id = str(uuid.uuid4())[:8]
    st.session_state.current_session_id = new_id
    create_session(new_id, "New Session")

if "messages" not in st.session_state:
    st.session_state.messages = get_session_messages(st.session_state.current_session_id)

if "total_tokens_used" not in st.session_state:
    st.session_state.total_tokens_used = 0
if "estimated_cost" not in st.session_state:
    st.session_state.estimated_cost = 0.0

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

env_api_key = os.getenv("AGENTROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
env_base_url = os.getenv("AGENTROUTER_BASE_URL", "https://agentrouter.ai/v1")

api_key = st.sidebar.text_input("AgentRouter API Key", value=env_api_key, type="password")
base_url = st.sidebar.text_input("Base API URL", value=env_base_url)

models_list = fetch_available_models(api_key, base_url)

mode = st.sidebar.radio("Mode", ["Standard Assistant Chat", "Side-by-Side Model Comparison", "Multi-Agent Security Pipeline"])

if mode == "Standard Assistant Chat":
    selected_model = st.sidebar.selectbox("Select Model", options=models_list, index=0)
    custom_model = st.sidebar.text_input("Or custom model name:", value="", key="custom_single")
    model_to_use = custom_model.strip() if custom_model.strip() else selected_model
elif mode == "Side-by-Side Model Comparison":
    st.sidebar.markdown("**Select Models for Comparison:**")
    model_a = st.sidebar.selectbox("Model A", options=models_list, index=0, key="model_a")
    model_b = st.sidebar.selectbox("Model B", options=models_list, index=min(1, len(models_list)-1), key="model_b")

# System Persona / Prompt Presets
selected_preset_name = st.sidebar.selectbox("Select System Persona Preset", list(SYSTEM_PRESETS.keys()), index=0)
system_prompt_text = st.sidebar.text_area("System Prompt", value=SYSTEM_PRESETS[selected_preset_name], height=80)

# Feature Toggles
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Security & Search Settings")
enable_web_search = st.sidebar.checkbox("Enable Live Web Search", value=False)
auto_redact_pii = st.sidebar.checkbox("Auto-Redact Credentials & PII prior to sending", value=True)
auto_security_scan = st.sidebar.checkbox("Run Heuristic Vulnerability Scan on uploaded code", value=True)
enable_ast_scan = st.sidebar.checkbox("Run AST Syntax Tree Scan on Python code", value=True)
enable_rag_indexing = st.sidebar.checkbox("Enable RAG Semantic Search over Documents", value=True)

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
document_chunks = []
code_files_for_remediation = {}

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
            elif parsed_file["file_type"] == "document":
                # Security Scan (Regex + AST)
                f_results = []
                if auto_security_scan:
                    f_results.extend(scan_code_for_vulnerabilities(parsed_file["content"], parsed_file["filename"]))
                if enable_ast_scan and (ext == "py" or not ext):
                    f_results.extend(analyze_python_ast(parsed_file["content"], parsed_file["filename"]))

                if f_results:
                    security_scan_results.extend(f_results)
                    code_files_for_remediation[parsed_file["filename"]] = {
                        "content": parsed_file["content"],
                        "findings": f_results
                    }

                # RAG Indexing
                if enable_rag_indexing:
                    raw_chunks = chunk_text(parsed_file["content"])
                    for c in raw_chunks:
                        document_chunks.append({"source": parsed_file["filename"], "text": c})

if security_scan_results:
    st.warning("⚠️ **Static & AST Security Findings in uploaded code:**")
    for warn in security_scan_results:
        st.write(warn)

    with st.expander("🛠️ Security Remediation & PDF Report Generator"):
        for fname, file_data in code_files_for_remediation.items():
            patch_diff = generate_remediation_diff(fname, file_data["content"], file_data["findings"])
            st.code(patch_diff, language="diff")

            pdf_bytes = generate_pdf_audit_report(fname, file_data["findings"], patch_diff)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.download_button(
                    label=f"📥 Download {fname}.patch",
                    data=patch_diff,
                    file_name=f"{fname}.patch",
                    mime="text/plain"
                )
            with col_p2:
                st.download_button(
                    label=f"📄 Download PDF Audit Report ({fname}.pdf)",
                    data=pdf_bytes,
                    file_name=f"{fname}_audit_report.pdf",
                    mime="application/pdf"
                )

# CSV Data Visualization Section
if csv_datasets:
    for ds in csv_datasets:
        render_data_analysis_ui(ds["df"], ds["filename"])
    st.markdown("---")

# Mode 3: Multi-Agent Pipeline Execution
if mode == "Multi-Agent Security Pipeline":
    st.subheader("🤖 Multi-Agent Autonomous Pipeline Execution")
    st.write("Decomposes tasks across specialized sub-agents: Sanitizer -> Code Inspector -> Patch Generator -> Executive Summarizer.")

    agent_code_input = st.text_area("Source Code for Agent Pipeline", value="eval('import os');\nquery = 'SELECT * FROM users WHERE id=' + user_id", height=150)
    agent_filename = st.text_input("Target Filename", value="script.py")

    if st.button("Run Multi-Agent Pipeline"):
        with st.status("🤖 Multi-Agent Pipeline Execution...", expanded=True) as status:
            status.write("Phase 1: Input Sanitization & PII Redaction...")
            pipeline = SecurityTaskPipeline(agent_filename, agent_code_input)
            status.write("Phase 2: Code Inspection & AST Vulnerability Analysis...")
            result = pipeline.execute_pipeline()
            status.write("Phase 3: Remediation Patch Generation...")
            status.update(label="✅ Multi-Agent Pipeline Completed Successfully!", state="complete", expanded=False)

        st.markdown("### 📋 Agent Workflow Logs")
        for log in result["agent_logs"]:
            st.write(log)

        st.markdown("### 📊 Executive Summary")
        st.info(result["summary"])

        if result["findings"]:
            st.markdown("### ⚠️ Identified Findings")
            for f in result["findings"]:
                st.write(f)

            st.markdown("### 🛠️ Generated Remediation Patch")
            st.code(result["patch_diff"], language="diff")

# Persistent Sessions Management UI
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Saved Conversations")

all_sessions = get_all_sessions()
session_options = {s["id"]: f"{s['title']} ({s['id']})" for s in all_sessions}

col_s1, col_s2 = st.sidebar.columns([3, 1])
with col_s1:
    selected_sess_id = st.selectbox(
        "Select Session",
        options=list(session_options.keys()),
        format_func=lambda x: session_options[x],
        index=list(session_options.keys()).index(st.session_state.current_session_id) if st.session_state.current_session_id in session_options else 0
    )

if selected_sess_id != st.session_state.current_session_id:
    st.session_state.current_session_id = selected_sess_id
    st.session_state.messages = get_session_messages(selected_sess_id)
    st.rerun()

with col_s2:
    if st.button("➕ New"):
        new_id = str(uuid.uuid4())[:8]
        create_session(new_id, f"Session {new_id}")
        st.session_state.current_session_id = new_id
        st.session_state.messages = []
        st.rerun()

if st.sidebar.button("Clear / Reset Session Messages"):
    delete_session(st.session_state.current_session_id)
    create_session(st.session_state.current_session_id, "Reset Session")
    st.session_state.messages = []
    st.session_state.total_tokens_used = 0
    st.session_state.estimated_cost = 0.0
    st.rerun()

if st.session_state.messages:
    md_export = export_chat_to_markdown(st.session_state.messages)
    json_export = export_chat_to_json(st.session_state.messages)
    col_ex1, col_ex2 = st.sidebar.columns(2)
    with col_ex1:
        st.download_button("📥 Export MD", md_export, file_name=f"chat_{st.session_state.current_session_id}.md", mime="text/markdown")
    with col_ex2:
        st.download_button("📥 Export JSON", json_export, file_name=f"chat_{st.session_state.current_session_id}.json", mime="application/json")

st.sidebar.metric("Total Estimated Tokens", st.session_state.total_tokens_used)
st.sidebar.metric("Total Estimated Cost ($)", f"${st.session_state.estimated_cost:.5f}")

# Display Suggestion Prompt Cards when conversation is empty
if len(st.session_state.messages) == 0 and mode in ["Standard Assistant Chat", "Side-by-Side Model Comparison"]:
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("""
        <div class="suggestion-card">
            <div class="suggestion-title">🛡️ Security & AST Code Audit</div>
            <div class="suggestion-desc">Upload Python/source code to scan for OWASP vulnerabilities & AST syntax trees.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="suggestion-card">
            <div class="suggestion-title">⚖️ Side-by-Side Model Comparison</div>
            <div class="suggestion-desc">Compare real-time LLM responses from GPT-4o, Claude, DeepSeek, or Llama.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown("""
        <div class="suggestion-card">
            <div class="suggestion-title">📚 Document RAG & Web Search</div>
            <div class="suggestion-desc">Ask questions across uploaded PDFs/documents or enable live web search context.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="suggestion-card">
            <div class="suggestion-title">🤖 Autonomous Multi-Agent Pipeline</div>
            <div class="suggestion-desc">Run autonomous multi-agent pipelines for code inspection and patch generation.</div>
        </div>
        """, unsafe_allow_html=True)

# Display Chat History
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# User Chat Input (for Chat and Comparison modes)
if mode in ["Standard Assistant Chat", "Side-by-Side Model Comparison"]:
    if prompt := st.chat_input("Ask anything, analyze security, inspect documents, or search web..."):
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
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt_to_send)

            st.session_state.messages.append({"role": "user", "content": prompt_to_send})
            save_message(st.session_state.current_session_id, "user", prompt_to_send)

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

            # Web Search Context Integration
            web_context_str = ""
            if enable_web_search:
                with st.status("🔍 Searching live web for context...", expanded=False) as status:
                    search_results = perform_web_search(prompt_to_send)
                    if search_results:
                        web_context_str = format_search_context(search_results)
                        status.update(label=f"🌐 Retrieved {len(search_results)} live web search results", state="complete")
                    else:
                        status.update(label="🌐 Web search completed (0 results)", state="complete")

            # RAG Context Integration
            rag_context_str = ""
            if enable_rag_indexing and document_chunks:
                with st.status("📚 Scanning uploaded documents (RAG)...", expanded=False) as status:
                    top_matches = search_chunks(prompt_to_send, document_chunks, top_k=3)
                    if top_matches:
                        rag_context_str = "--- Relevant Document Chunks (RAG) ---\n" + "\n".join(
                            [f"[{m['source']} (Score: {m['score']})]: {m['text']}" for m in top_matches]
                        )
                        status.update(label=f"📄 Matched {len(top_matches)} document chunk(s)", state="complete")
                    else:
                        status.update(label="📄 RAG scan completed (0 matches)", state="complete")

            # Merge additional context into user prompt for API
            augmented_user_prompt = prompt_to_send
            if web_context_str:
                augmented_user_prompt = f"{web_context_str}\n\n{augmented_user_prompt}"
            if rag_context_str:
                augmented_user_prompt = f"{rag_context_str}\n\n{augmented_user_prompt}"

            api_messages = prepare_messages_for_api(
                chat_history=history_to_send,
                attached_files=processed_files,
                user_prompt=augmented_user_prompt
            )

            in_tokens = estimate_tokens(str(api_messages))

            if mode == "Standard Assistant Chat":
                with st.chat_message("assistant", avatar="🤖"):
                    try:
                        client = get_agentrouter_client(api_key, base_url)
                        response = client.chat.completions.create(
                            model=model_to_use,
                            messages=api_messages,
                            stream=True
                        )

                        def stream_gen(res):
                            for chunk in res:
                                if chunk.choices and chunk.choices[0].delta.content:
                                    yield chunk.choices[0].delta.content

                        full_resp = st.write_stream(stream_gen(response))
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                        save_message(st.session_state.current_session_id, "assistant", full_resp)

                        out_tokens = estimate_tokens(full_resp)
                        cost = calculate_cost(model_to_use, in_tokens, out_tokens)
                        st.session_state.total_tokens_used += (in_tokens + out_tokens)
                        st.session_state.estimated_cost += cost

                    except Exception as e:
                        err_msg = str(e)
                        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                            st.error(f"Error from AgentRouter API: Request timed out. Please verify that your API key is valid and active, or try selecting a different model or Base API URL (e.g. https://openrouter.ai/api/v1).")
                        else:
                            st.error(f"Error from AgentRouter API: {err_msg}")

            else: # Side-by-Side Model Comparison
                col_a, col_b = st.columns(2)
                resp_a_text = ""
                resp_b_text = ""

                def make_stream_gen(res):
                    def gen():
                        for chunk in res:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    return gen()

                with col_a:
                    st.subheader(f"🤖 {model_a}")
                    try:
                        client = get_agentrouter_client(api_key, base_url)
                        resp_a = client.chat.completions.create(model=model_a, messages=api_messages, stream=True)
                        resp_a_text = st.write_stream(make_stream_gen(resp_a))
                    except Exception as e:
                        st.error(f"Error ({model_a}): {str(e)}")

                with col_b:
                    st.subheader(f"🤖 {model_b}")
                    try:
                        client = get_agentrouter_client(api_key, base_url)
                        resp_b = client.chat.completions.create(model=model_b, messages=api_messages, stream=True)
                        resp_b_text = st.write_stream(make_stream_gen(resp_b))
                    except Exception as e:
                        st.error(f"Error ({model_b}): {str(e)}")

                combined_resp = f"**[{model_a} Response]:**\n{resp_a_text}\n\n---\n\n**[{model_b} Response]:**\n{resp_b_text}"
                st.session_state.messages.append({"role": "assistant", "content": combined_resp})
                save_message(st.session_state.current_session_id, "assistant", combined_resp)

                out_tokens = estimate_tokens(resp_a_text + resp_b_text)
                cost_a = calculate_cost(model_a, in_tokens, estimate_tokens(resp_a_text))
                cost_b = calculate_cost(model_b, in_tokens, estimate_tokens(resp_b_text))
                st.session_state.total_tokens_used += (in_tokens * 2 + out_tokens)
                st.session_state.estimated_cost += (cost_a + cost_b)
