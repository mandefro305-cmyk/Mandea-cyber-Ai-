import io
import unittest
from PIL import Image
import docx
import pandas as pd

from file_parser import (
    parse_text_file,
    parse_pdf_file,
    parse_docx_file,
    encode_image_to_base64,
    process_uploaded_file
)
from api_client import prepare_messages_for_api, fetch_available_models
from config import estimate_tokens, calculate_cost, SYSTEM_PRESETS
from security_utils import redact_sensitive_data, scan_code_for_vulnerabilities
from data_utils import parse_csv_file
from session_utils import export_chat_to_markdown, export_chat_to_json

class DummyUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

class TestAppFeatures(unittest.TestCase):

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
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "user")
        self.assertIn("Doc content", messages[2]["content"])
        self.assertIn("Summarize this document", messages[2]["content"])

    def test_fetch_available_models_fallback(self):
        models = fetch_available_models(api_key="", base_url="https://agentrouter.ai/v1")
        self.assertTrue(len(models) > 0)
        self.assertIn("gpt-4o", models)

    def test_redact_sensitive_data(self):
        sample = "My api_key='sk-12345678901234567890' and email test@example.com"
        redacted, count = redact_sensitive_data(sample)
        self.assertTrue(count >= 2)
        self.assertNotIn("sk-12345678901234567890", redacted)
        self.assertNotIn("test@example.com", redacted)

    def test_scan_code_for_vulnerabilities(self):
        vulnerable_code = "eval('import os');\nquery = 'SELECT * FROM users WHERE id=' + user_id"
        findings = scan_code_for_vulnerabilities(vulnerable_code)
        self.assertTrue(len(findings) >= 2)

    def test_parse_csv_file(self):
        csv_data = b"col1,col2\n1,10\n2,20\n3,30"
        res = parse_csv_file(csv_data, "data.csv")
        self.assertTrue(res["success"])
        self.assertEqual(res["df"].shape, (3, 2))

    def test_chat_export(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        md = export_chat_to_markdown(messages)
        js = export_chat_to_json(messages)
        self.assertIn("# Chat Session Export", md)
        self.assertIn("Hi there", js)

    def test_token_and_cost_estimation(self):
        tokens = estimate_tokens("Short sentence for token count estimation.")
        cost = calculate_cost("gpt-4o", 1000, 500)
        self.assertTrue(tokens > 0)
        self.assertTrue(cost > 0)

if __name__ == "__main__":
    unittest.main()
