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
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authenticated state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = "Guest"
if "user_role" not in st.session_state:
    st.session_state.user_role = "guest"

# ChatGPT Aesthetic Injection
st.markdown("""
<style>
    /* Main container and font setup */
    .stApp {
        background-color: #212121;
        color: #ececec;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #171717 !important;
        border-right: 1px solid #2f2f2f !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* ChatGPT New Chat Button */
    .new-chat-btn {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 10px;
        width: 100%;
        padding: 10px 14px;
        background-color: transparent;
        border: 1px solid #424242;
        border-radius: 8px;
        color: #ffffff;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .new-chat-btn:hover {
        background-color: #2f2f2f;
    }

    /* Top Navigation Model Selector Header */
    .top-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 1rem 1rem 1rem;
        border-bottom: 1px solid #2f2f2f;
        margin-bottom: 1.5rem;
    }

    /* Chat Greeting Title */
    .hero-title {
        font-size: 2rem;
        font-weight: 600;
        text-align: center;
        margin-top: 3rem;
        margin-bottom: 2rem;
        color: #f3f3f3;
    }

    /* Suggestion Cards */
    .suggestion-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        max-width: 760px;
        margin: 0 auto 2rem auto;
    }

    .suggestion-card {
        background-color: #212121;
        border: 1px solid #383838;
        border-radius: 12px;
        padding: 14px 16px;
        cursor: pointer;
        transition: border-color 0.2s, background-color 0.2s;
    }

    .suggestion-card:hover {
        background-color: #2f2f2f;
        border-color: #555555;
    }

    .suggestion-title {
        font-size: 0.92rem;
        font-weight: 600;
        color: #ececec;
        margin-bottom: 4px;
    }

    .suggestion-sub {
        font-size: 0.82rem;
        color: #8e8e93;
    }

    /* Custom Chat Input Styling */
    .stChatInputContainer {
        max-width: 780px !important;
        margin: 0 auto !important;
    }

    div[data-testid="stChatMessage"] {
        max-width: 800px;
        margin: 0 auto 0.8rem auto;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        background-color: #212121;
    }

    /* Hide default Streamlit elements for a cleaner UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Session State Initializations
if "current_session_id" not in st.session_state:
    new_id = str(uuid.uuid4())[:8]
    st.session_state.current_session_id = new_id
    create_session(new_id, "New Chat")

if "messages" not in st.session_state:
    st.session_state.messages = get_session_messages(st.session_state.current_session_id)

if "total_tokens_used" not in st.session_state:
    st.session_state.total_tokens_used = 0
if "estimated_cost" not in st.session_state:
    st.session_state.estimated_cost = 0.0

# SIDEBAR: ChatGPT style
with st.sidebar:
    # 1. New Chat Button
    if st.button("➕ New chat", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        create_session(new_id, "New Chat")
        st.session_state.current_session_id = new_id
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # 2. History List
    st.markdown("<div style='font-size: 0.8rem; color: #8e8e93; font-weight: 600; margin-bottom: 8px;'>CHATS</div>", unsafe_allow_html=True)
    all_sessions = get_all_sessions()
    for s in all_sessions:
        is_active = (s["id"] == st.session_state.current_session_id)
        btn_label = f"💬 {s['title'][:22]}" if not is_active else f"👉 {s['title'][:22]}"
        if st.button(btn_label, key=f"sess_{s['id']}", use_container_width=True):
            st.session_state.current_session_id = s["id"]
            st.session_state.messages = get_session_messages(s["id"])
            st.rerun()

    st.markdown("---")

    # 3. Mode & Settings Expander (Keeps API Key masked/secure)
    with st.expander("⚙️ Settings & System Persona"):
        env_api_key = os.getenv("AGENTROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
        env_base_url = os.getenv("AGENTROUTER_BASE_URL", "https://agentrouter.ai/v1")

        # Mask API key using password type and placeholder if env is set
        api_key = st.text_input(
            "API Key",
            value=env_api_key,
            type="password",
            help="Your AgentRouter / OpenRouter API Key"
        )
        base_url = st.text_input("Base API URL", value=env_base_url)

        selected_preset_name = st.selectbox("System Persona", list(SYSTEM_PRESETS.keys()), index=0)
        system_prompt_text = st.text_area("System Prompt", value=SYSTEM_PRESETS[selected_preset_name], height=70)

        enable_web_search = st.checkbox("Live Web Search", value=False)
        auto_redact_pii = st.checkbox("Auto-Redact Credentials & PII", value=True)
        auto_security_scan = st.checkbox("Code Vulnerability Scan", value=True)
        enable_ast_scan = st.checkbox("AST Python Scan", value=True)
        enable_rag_indexing = st.checkbox("Document RAG", value=True)

    # 4. Attachments Section
    with st.expander("📂 Attachments & Files"):
        uploaded_files = st.file_uploader("Attach files (PDF, CSV, Code, Images)", accept_multiple_files=True)

    # 5. Account / Auth Section at Sidebar Bottom
    st.markdown("---")
    if not st.session_state.authenticated:
        with st.expander("🔐 Login / Register"):
            auth_mode = st.radio("Account Action", ["Login", "Register"])
            u_input = st.text_input("Username", key="auth_u")
            p_input = st.text_input("Password", type="password", key="auth_p")

            if auth_mode == "Login":
                if st.button("Login", use_container_width=True):
                    success, msg, role = authenticate_user(u_input, p_input)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = u_input
                        st.session_state.user_role = role
                        st.success(f"Logged in as {u_input}")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                if st.button("Register", use_container_width=True):
                    success, msg = register_user(u_input, p_input)
                    if success:
                        st.success("Account created! Please login.")
                    else:
                        st.error(msg)
    else:
        st.markdown(f"👤 **{st.session_state.username}** ({st.session_state.user_role})")
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = "Guest"
            st.session_state.user_role = "guest"
            st.rerun()

    # Session Export & Usage
    if st.session_state.messages:
        md_export = export_chat_to_markdown(st.session_state.messages)
        st.download_button("📥 Export Chat (.md)", md_export, file_name=f"chat_{st.session_state.current_session_id}.md", mime="text/markdown", use_container_width=True)

# Parse uploaded files if present
parsed_attached_files = []
csv_datasets = []
security_scan_results = []
document_chunks = []
code_files_for_remediation = {}

if 'uploaded_files' in locals() and uploaded_files:
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

            if parsed_file["file_type"] == "document":
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

                if enable_rag_indexing:
                    raw_chunks = chunk_text(parsed_file["content"])
                    for c in raw_chunks:
                        document_chunks.append({"source": parsed_file["filename"], "text": c})

# MAIN INTERFACE
models_list = fetch_available_models(api_key, base_url)

# Top Bar: ChatGPT Model Switcher
col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    mode = st.selectbox("Mode", ["Standard Assistant Chat", "Side-by-Side Model Comparison", "Multi-Agent Security Pipeline"], label_visibility="collapsed")
with col_top2:
    if mode == "Standard Assistant Chat":
        selected_model = st.selectbox("Model", options=models_list, index=0, label_visibility="collapsed")
        model_to_use = selected_model
    else:
        model_to_use = models_list[0] if models_list else "gpt-4o"

if mode == "Side-by-Side Model Comparison":
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        model_a = st.selectbox("Model A", options=models_list, index=0, key="model_a_select")
    with col_m2:
        model_b = st.selectbox("Model B", options=models_list, index=min(1, len(models_list)-1), key="model_b_select")

# Render Security Findings & CSV Data if available
if security_scan_results:
    st.warning("⚠️ **Security Findings in attached files:**")
    for warn in security_scan_results:
        st.write(warn)

if csv_datasets:
    for ds in csv_datasets:
        render_data_analysis_ui(ds["df"], ds["filename"])

# Mode 3: Multi-Agent Security Pipeline UI
if mode == "Multi-Agent Security Pipeline":
    st.markdown("<h3 style='text-align: center;'>🤖 Multi-Agent Security Pipeline</h3>", unsafe_allow_html=True)
    agent_code_input = st.text_area("Source Code to Audit", value="eval('import os');\nquery = 'SELECT * FROM users WHERE id=' + user_id", height=150)
    agent_filename = st.text_input("Target Filename", value="script.py")

    if st.button("Execute Multi-Agent Audit", use_container_width=True):
        with st.status("🤖 Multi-Agent Workflow Running...", expanded=True) as status:
            pipeline = SecurityTaskPipeline(agent_filename, agent_code_input)
            result = pipeline.execute_pipeline()
            status.update(label="✅ Audit Completed!", state="complete", expanded=False)

        st.markdown("### 📋 Log Output")
        for log in result["agent_logs"]:
            st.write(log)

        st.info(result["summary"])

        if result["findings"]:
            st.markdown("### ⚠️ Findings")
            for f in result["findings"]:
                st.write(f)
            st.markdown("### 🛠️ Remediation Patch")
            st.code(result["patch_diff"], language="diff")

# ChatGPT Empty State View
if len(st.session_state.messages) == 0 and mode in ["Standard Assistant Chat", "Side-by-Side Model Comparison"]:
    st.markdown("<div class='hero-title'>What can I help with today?</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='suggestion-grid'>
        <div class='suggestion-card'>
            <div class='suggestion-title'>🛡️ Security & AST Audit</div>
            <div class='suggestion-sub'>Scan code for OWASP vulnerabilities & AST structures</div>
        </div>
        <div class='suggestion-card'>
            <div class='suggestion-title'>⚖️ Model Comparison</div>
            <div class='suggestion-sub'>Compare response quality side-by-side across LLMs</div>
        </div>
        <div class='suggestion-card'>
            <div class='suggestion-title'>📚 RAG Document Analysis</div>
            <div class='suggestion-sub'>Extract insights & search chunks from attached documents</div>
        </div>
        <div class='suggestion-card'>
            <div class='suggestion-title'>🤖 Multi-Agent Workflows</div>
            <div class='suggestion-sub'>Decompose complex security tasks with specialized sub-agents</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render Chat History
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# User Chat Input Bar
if mode in ["Standard Assistant Chat", "Side-by-Side Model Comparison"]:
    if prompt := st.chat_input("Message Mâñđ€å Åî..."):
        if not api_key:
            st.error("Please enter your API key in the sidebar settings.")
        else:
            prompt_to_send = prompt
            if auto_redact_pii:
                prompt_to_send, r_count = redact_sensitive_data(prompt)

            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt_to_send)

            st.session_state.messages.append({"role": "user", "content": prompt_to_send})
            save_message(st.session_state.current_session_id, "user", prompt_to_send)

            history_to_send = st.session_state.messages[:-1]
            if system_prompt_text.strip():
                history_to_send = [{"role": "system", "content": system_prompt_text.strip()}] + history_to_send

            processed_files = []
            for pf in parsed_attached_files:
                file_copy = dict(pf)
                if auto_redact_pii and file_copy["file_type"] == "document":
                    file_copy["content"], _ = redact_sensitive_data(file_copy["content"])
                processed_files.append(file_copy)

            # Web search context
            web_context_str = ""
            if enable_web_search:
                with st.spinner("Searching live web..."):
                    search_results = perform_web_search(prompt_to_send)
                    if search_results:
                        web_context_str = format_search_context(search_results)

            # RAG context
            rag_context_str = ""
            if enable_rag_indexing and document_chunks:
                with st.spinner("Scanning documents..."):
                    top_matches = search_chunks(prompt_to_send, document_chunks, top_k=3)
                    if top_matches:
                        rag_context_str = "--- Relevant Document Chunks (RAG) ---\n" + "\n".join(
                            [f"[{m['source']} (Score: {m['score']})]: {m['text']}" for m in top_matches]
                        )

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
                        from api_client import stream_response_generator, extract_response_text
                        client = get_agentrouter_client(api_key, base_url)

                        full_resp = ""
                        try:
                            response = client.chat.completions.create(
                                model=model_to_use,
                                messages=api_messages,
                                stream=True
                            )
                            full_resp = st.write_stream(stream_response_generator(response))
                        except Exception:
                            full_resp = ""

                        # Fallback to non-streaming request if stream is empty or fails
                        if not full_resp:
                            fallback_resp = client.chat.completions.create(
                                model=model_to_use,
                                messages=api_messages,
                                stream=False
                            )
                            full_resp = extract_response_text(fallback_resp)
                            if full_resp:
                                st.markdown(full_resp)

                        if full_resp:
                            st.session_state.messages.append({"role": "assistant", "content": full_resp})
                            save_message(st.session_state.current_session_id, "assistant", full_resp)

                            out_tokens = estimate_tokens(full_resp)
                            cost = calculate_cost(model_to_use, in_tokens, out_tokens)
                            st.session_state.total_tokens_used += (in_tokens + out_tokens)
                            st.session_state.estimated_cost += cost
                        else:
                            st.error(f"The API endpoint ({base_url}) returned an empty response for model `{model_to_use}`. Please check model availability or try selecting `gpt-4o` or `claude-3-5-sonnet`.")

                    except Exception as e:
                        err_msg = str(e)
                        st.error(f"Error from API ({base_url}): {err_msg}")

            else:  # Side-by-Side Model Comparison
                col_a, col_b = st.columns(2)
                resp_a_text = ""
                resp_b_text = ""
                from api_client import stream_response_generator

                with col_a:
                    st.subheader(f"🤖 {model_a}")
                    try:
                        client = get_agentrouter_client(api_key, base_url)
                        resp_a = client.chat.completions.create(model=model_a, messages=api_messages, stream=True)
                        resp_a_text = st.write_stream(stream_response_generator(resp_a))
                    except Exception as e:
                        st.error(f"Error ({model_a}): {str(e)}")

                with col_b:
                    st.subheader(f"🤖 {model_b}")
                    try:
                        client = get_agentrouter_client(api_key, base_url)
                        resp_b = client.chat.completions.create(model=model_b, messages=api_messages, stream=True)
                        resp_b_text = st.write_stream(stream_response_generator(resp_b))
                    except Exception as e:
                        st.error(f"Error ({model_b}): {str(e)}")

                combined_resp = f"**[{model_a} Response]:**\n{resp_a_text}\n\n---\n\n**[{model_b} Response]:**\n{resp_b_text}"
                st.session_state.messages.append({"role": "assistant", "content": combined_resp})
                save_message(st.session_state.current_session_id, "assistant", combined_resp)
