import json
from security_utils import scan_code_for_vulnerabilities, redact_sensitive_data
from ast_utils import analyze_python_ast
from remediation_utils import generate_remediation_diff

class SecurityTaskPipeline:
    """
    Multi-Agent sequential workflow pipeline.
    Decomposes task into sub-agent steps:
    1. Sanitize & Redact Input Agent
    2. Static & AST Code Analysis Agent
    3. Security Remediation Patch Agent
    4. Executive Summary Agent
    """

    def __init__(self, filename: str, code: str):
        self.filename = filename
        self.code = code
        self.logs = []

    def execute_pipeline(self) -> dict:
        self.logs.append("🚀 [Agent 1: Sanitizer] Redacting PII and sensitive tokens from input...")
        clean_code, count = redact_sensitive_data(self.code)
        self.logs.append(f"✓ [Agent 1] Redacted {count} sensitive item(s).")

        self.logs.append("🔍 [Agent 2: Code Inspector] Performing regex heuristic & AST syntax tree scan...")
        regex_findings = scan_code_for_vulnerabilities(clean_code, self.filename)
        ast_findings = analyze_python_ast(clean_code, self.filename) if self.filename.endswith(".py") or not self.filename else []
        all_findings = regex_findings + ast_findings
        self.logs.append(f"✓ [Agent 2] Identified {len(all_findings)} security finding(s).")

        self.logs.append("🛠️ [Agent 3: Patch Generator] Constructing automated git diff remediation patch...")
        patch_diff = generate_remediation_diff(self.filename, clean_code, all_findings)
        self.logs.append("✓ [Agent 3] Remediation patch generated successfully.")

        self.logs.append("📊 [Agent 4: Executive Summarizer] Finalizing task report...")
        summary = f"Audit completed for '{self.filename}'. Status: {'⚠️ Vulnerabilities Found' if all_findings else '✅ Clean'}. Total Findings: {len(all_findings)}."
        self.logs.append("✓ [Agent 4] Executive summary complete.")

        return {
            "filename": self.filename,
            "clean_code": clean_code,
            "findings": all_findings,
            "patch_diff": patch_diff,
            "summary": summary,
            "agent_logs": self.logs
        }
