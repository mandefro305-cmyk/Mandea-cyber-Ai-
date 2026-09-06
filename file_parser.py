import io
import base64
from PIL import Image
from pypdf import PdfReader
import docx

def parse_text_file(file_bytes: bytes, filename: str) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception as e:
            return f"[Error decoding text file {filename}: {str(e)}]"

def parse_pdf_file(file_bytes: bytes, filename: str) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        extracted_text = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(f"--- Page {idx + 1} ---\n{text}")
        return "\n\n".join(extracted_text) if extracted_text else "[PDF file contains no extractable text]"
    except Exception as e:
        return f"[Error reading PDF file {filename}: {str(e)}]"

def parse_docx_file(file_bytes: bytes, filename: str) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(full_text) if full_text else "[DOCX file contains no extractable text]"
    except Exception as e:
        return f"[Error reading DOCX file {filename}: {str(e)}]"

def encode_image_to_base64(file_bytes: bytes) -> tuple[str, str]:
    """Returns (base64_str, mime_type)"""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        fmt = (img.format or "PNG").lower()
        if fmt == "jpg":
            fmt = "jpeg"
        mime_type = f"image/{fmt}"
        b64_str = base64.b64encode(file_bytes).decode("utf-8")
        return b64_str, mime_type
    except Exception as e:
        raise ValueError(f"Failed to process image: {str(e)}")

def process_uploaded_file(uploaded_file) -> dict:
    """
    Processes an uploaded file from Streamlit.
    Returns dict with keys:
    - filename: str
    - file_type: 'image' or 'document'
    - content: extracted string text (for document) or base64 data URL (for image)
    - mime_type: str (if image)
    """
    filename = uploaded_file.name
    file_bytes = uploaded_file.getvalue()
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    image_extensions = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}

    if ext in image_extensions:
        b64_str, mime_type = encode_image_to_base64(file_bytes)
        return {
            "filename": filename,
            "file_type": "image",
            "content": f"data:{mime_type};base64,{b64_str}",
            "mime_type": mime_type,
            "b64": b64_str
        }
    elif ext == "pdf":
        text = parse_pdf_file(file_bytes, filename)
        return {
            "filename": filename,
            "file_type": "document",
            "content": text
        }
    elif ext in {"docx", "doc"}:
        text = parse_docx_file(file_bytes, filename)
        return {
            "filename": filename,
            "file_type": "document",
            "content": text
        }
    else:
        # Treat as plain text / code / csv / json / etc.
        text = parse_text_file(file_bytes, filename)
        return {
            "filename": filename,
            "file_type": "document",
            "content": text
        }
