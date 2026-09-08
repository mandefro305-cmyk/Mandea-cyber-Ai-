from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from security_utils import scan_code_for_vulnerabilities, redact_sensitive_data
from ast_utils import analyze_python_ast
from rag_utils import chunk_text, search_chunks
from remediation_utils import generate_remediation_diff

app = FastAPI(
    title="Multi-Modal AI Assistant & Security API",
    description="Headless API for security auditing, PII redaction, RAG search, and code remediation.",
    version="1.0.0"
)

class AuditRequest(BaseModel):
    filename: str
    code: str

class RedactRequest(BaseModel):
    text: str

class RAGRequest(BaseModel):
    query: str
    documents: List[dict] # [{"filename": str, "content": str}]

@app.get("/")
def read_root():
    return {"status": "online", "message": "Multi-Modal AI Assistant REST API is active."}

@app.post("/api/v1/audit")
def audit_code(req: AuditRequest):
    regex_findings = scan_code_for_vulnerabilities(req.code, req.filename)
    ast_findings = []
    if req.filename.endswith(".py") or not req.filename:
        ast_findings = analyze_python_ast(req.code, req.filename)

    all_findings = regex_findings + ast_findings
    patch_diff = generate_remediation_diff(req.filename, req.code, all_findings)

    return {
        "filename": req.filename,
        "total_findings": len(all_findings),
        "findings": all_findings,
        "patch_diff": patch_diff
    }

@app.post("/api/v1/redact")
def redact_text(req: RedactRequest):
    redacted, count = redact_sensitive_data(req.text)
    return {
        "redacted_text": redacted,
        "redactions_count": count
    }

@app.post("/api/v1/rag-search")
def rag_search(req: RAGRequest):
    chunks = []
    for doc in req.documents:
        fname = doc.get("filename", "Doc")
        c_list = chunk_text(doc.get("content", ""))
        for c in c_list:
            chunks.append({"source": fname, "text": c})

    matches = search_chunks(req.query, chunks, top_k=3)
    return {
        "query": req.query,
        "matches": matches
    }
