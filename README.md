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

## 🚂 Railway Deployment & Persistent Volume Setup

### 1. Fix 502 Bad Gateway / Network Port Configuration
If Railway shows `502 Bad Gateway` on deployment:
1. Open your service settings on **Railway.app**.
2. Go to **Settings** -> **Networking** -> **PORT**.
3. Ensure the Port setting is empty (so Railway automatically sets `PORT`) or set explicitly to:
   ```text
   8501
   ```
4. Under **Healthcheck Path**, set the healthcheck path to:
   ```text
   /_stcore/health
   ```

### 2. Add a Persistent Volume on Railway
To ensure persistent data storage (saved sessions, user logins, chat history) across container redeployments:
1. Open your project on **[Railway.app](https://railway.app)**.
2. Select **+ New** -> **Volume** and attach it to your service.
3. Set the **Mount Path** to:
   ```text
   /app/data
   ```
4. Set the environment variable in Railway Service Variables:
   ```env
   DATA_DIR=/app/data
   ```

---

## 🔑 Environment Variables Reference

| Variable Name | Description | Default / Example |
|---|---|---|
| `DATA_DIR` | Path to directory where SQLite DB is stored | `/app/data` (for Railway Volume) or `.` |
| `AGENTROUTER_API_KEY` | AgentRouter or OpenRouter API key | `sk-or-...` |
| `AGENTROUTER_BASE_URL` | API Base URL | `https://agentrouter.ai/v1` |
| `PORT` | Dynamic HTTP port provided by Railway | `8501` |

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
