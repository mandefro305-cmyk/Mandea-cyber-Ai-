import io
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

class DummyUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

class TestFileParserAndAPI(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
