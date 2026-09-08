import io
import os
import uuid
import unittest
from PIL import Image
import docx

from file_parser import (
    parse_text_file,
    parse_pdf_file,
    parse_docx_file,
    encode_image_to_base64,
    process_uploaded_file
)
from api_client import prepare_messages_for_api, fetch_available_models
from config import estimate_tokens, calculate_cost
from security_utils import redact_sensitive_data, scan_code_for_vulnerabilities
from ast_utils import analyze_python_ast
from data_utils import parse_csv_file
from session_utils import export_chat_to_markdown, export_chat_to_json
from db_utils import init_db, create_session, get_all_sessions, save_message, get_session_messages, delete_session
from rag_utils import chunk_text, search_chunks
from remediation_utils import generate_remediation_diff
from search_utils import format_search_context
from report_generator import generate_pdf_audit_report
from agent_engine import SecurityTaskPipeline
from auth_utils import register_user, authenticate_user

class DummyUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

class TestAppAllFeaturesExtended(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_parse_text_file(self):
        content = b"Hello, world! This is a test file."
        res = parse_text_file(content, "test.txt")
        self.assertEqual(res, "Hello, world! This is a test file.")

    def test_parse_docx_file(self):
        doc = docx.Document()
        doc.add_paragraph("Paragraph 1")
        doc.add_paragraph("Paragraph 2")
        bio = io.BytesIO()
        doc.save(bio)
        res = parse_docx_file(bio.getvalue(), "test.docx")
        self.assertIn("Paragraph 1", res)
        self.assertIn("Paragraph 2", res)

    def test_encode_image_to_base64(self):
        img = Image.new("RGB", (10, 10), color="red")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        b64_str, mime_type = encode_image_to_base64(bio.getvalue())
        self.assertEqual(mime_type, "image/png")
        self.assertTrue(len(b64_str) > 0)

    def test_process_uploaded_file_doc(self):
        dummy = DummyUploadedFile("notes.txt", b"Test notes content")
        res = process_uploaded_file(dummy)
        self.assertEqual(res["filename"], "notes.txt")
        self.assertEqual(res["file_type"], "document")
        self.assertEqual(res["content"], "Test notes content")

    def test_prepare_messages_for_api(self):
        attached = [
            {
                "filename": "doc.txt",
                "file_type": "document",
                "content": "Doc content"
            }
        ]
        history = [
            {"role": "user", "content": "Prior message"},
            {"role": "assistant", "content": "Prior response"}
        ]
        user_prompt = "Summarize this document"
        messages = prepare_messages_for_api(history, attached, user_prompt)

        self.assertEqual(len(messages), 3)

    def test_fetch_available_models_fallback(self):
        models = fetch_available_models(api_key="", base_url="https://agentrouter.ai/v1")
        self.assertTrue(len(models) > 0)
        self.assertIn("gpt-4o", models)

    def test_redact_sensitive_data(self):
        sample = "My api_key='sk-12345678901234567890' and email test@example.com"
        redacted, count = redact_sensitive_data(sample)
        self.assertTrue(count >= 2)
        self.assertNotIn("sk-12345678901234567890", redacted)

    def test_scan_code_for_vulnerabilities(self):
        vulnerable_code = "eval('import os');\nquery = 'SELECT * FROM users WHERE id=' + user_id"
        findings = scan_code_for_vulnerabilities(vulnerable_code)
        self.assertTrue(len(findings) >= 2)

    def test_ast_python_analysis(self):
        py_code = "import subprocess\neval('1+1')\nsubprocess.run('ls', shell=True)"
        ast_findings = analyze_python_ast(py_code, "test.py")
        self.assertTrue(len(ast_findings) >= 2)

    def test_pdf_report_generation(self):
        findings = ["Critical: Call to eval()"]
        diff = "--- a/test.py\n+++ b/test.py\n- eval()\n+ safe()"
        pdf_data = generate_pdf_audit_report("test.py", findings, diff)
        self.assertTrue(len(pdf_data) > 0)
        self.assertTrue(pdf_data.startswith(b"%PDF"))

    def test_agent_pipeline_execution(self):
        pipeline = SecurityTaskPipeline("script.py", "eval('1+1')")
        res = pipeline.execute_pipeline()
        self.assertEqual(res["filename"], "script.py")
        self.assertTrue(len(res["agent_logs"]) >= 4)
        self.assertTrue(len(res["findings"]) > 0)

    def test_user_authentication(self):
        uname = f"user_{str(uuid.uuid4())[:8]}"
        pwd = "securepassword123"
        success_reg, _ = register_user(uname, pwd, role="admin")
        self.assertTrue(success_reg)

        success_auth, _, role = authenticate_user(uname, pwd)
        self.assertTrue(success_auth)
        self.assertEqual(role, "admin")

        fail_auth, _, _ = authenticate_user(uname, "wrongpassword")
        self.assertFalse(fail_auth)

if __name__ == "__main__":
    unittest.main()
