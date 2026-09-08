# Mâñđ€å Åî (Mandea AI)

 mâñđ€å Åî is a multi-modal AI assistant application built with Streamlit, FastAPI, and AgentRouter / OpenRouter endpoints. It provides capabilities for standard assistant chat, multi-model comparison, security auditing, AST analysis, automated remediation, RAG over uploaded documents, and CSV data analysis.

---

## 🛠️ Features
- **Authentication & User Management**: SQLite-backed session & user management with password hashing.
- **Multi-Model Support**: Integrated with OpenAI-compatible APIs (AgentRouter / OpenRouter).
- **Side-by-Side Model Comparison**: Compare responses from two LLMs in real time.
- **Security & AST Scanner**: Automated regex and Python AST vulnerability scanning.
- **Patch & PDF Audit Report Generator**: Generate patch diffs and PDF audit reports for identified security issues.
- **Multi-Agent Pipeline**: Specialized autonomous agent pipeline for sanitization, code inspection, and remediation.
- **RAG & Web Search**: Document chunking, TF-IDF search, and live web search integration.
- **Headless REST API**: FastAPI server (`api_server.py`) exposing endpoint for audit, redaction, and RAG search.

---

## 🚂 Railway Persistent Volume Setup

To ensure persistent data storage (such as saved sessions, user logins, and chat history) across container redeployments on Railway:

### 1. Add a Volume in Railway
1. Open your project on **[Railway.app](https://railway.app)**.
2. Click on your project service canvas or select **+ New** -> **Volume**.
3. Select your service (`Mandea-cyber-Ai-` or your deployed service name) to attach the volume.
4. Set the **Mount Path** to:
   ```text
   /app/data
   ```

### 2. Configure Environment Variables
In your Railway Service Settings under **Variables**, set the following environment variable:
```env
DATA_DIR=/app/data
```

With `DATA_DIR=/app/data`, the application stores the SQLite database (`assistant_data.db`) at `/app/data/assistant_data.db`, ensuring that chat histories, registered user accounts, and saved sessions persist across deployments and container restarts.

---

## 🔑 Environment Variables Reference

| Variable Name | Description | Default / Example |
|---|---|---|
| `DATA_DIR` | Path to directory where SQLite DB is stored | `/app/data` (for Railway Volume) or `.` |
| `AGENTROUTER_API_KEY` | AgentRouter or OpenRouter API key | `sk-or-...` |
| `AGENTROUTER_BASE_URL` | API Base URL | `https://agentrouter.ai/v1` |

---

## 🚀 Running Locally

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Streamlit Web App**:
   ```bash
   streamlit run app.py
   ```

3. **Run Headless FastAPI REST Server**:
   ```bash
   uvicorn api_server:app --reload --port 8000
   ```

4. **Run Unit Tests**:
   ```bash
   python3 test_app.py
   ```
