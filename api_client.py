import os
import requests
import streamlit as st
from openai import OpenAI

def resolve_base_url(api_key: str, provided_base_url: str = "") -> str:
    """
    Resolves the appropriate Base API URL automatically based on the provided API key format if no explicit base URL is provided.
    """
    if provided_base_url and provided_base_url.strip():
        url = provided_base_url.strip().rstrip("/")
        # If user typed just host like agentrouter.org, append /v1
        if url.startswith("http://") or url.startswith("https://"):
            if not url.endswith("/v1") and not url.endswith("/api/v1"):
                if "openrouter" in url:
                    url = f"{url}/api/v1"
                else:
                    url = f"{url}/v1"
        return url

    # Automatic detection by API key prefix
    clean_key = (api_key or "").strip()
    if clean_key.startswith("sk-or-v1-"):
        return "https://openrouter.ai/api/v1"
    elif clean_key.startswith("sk-") and not clean_key.startswith("sk-or-"):
        return "https://api.openai.com/v1"

    env_url = os.getenv("AGENTROUTER_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    return "https://openrouter.ai/api/v1"

def get_agentrouter_client(api_key: str, base_url: str = "", timeout: float = 15.0):
    """
    Creates an OpenAI-compatible client for AgentRouter / OpenRouter with configurable timeout and retries.
    """
    if not api_key:
        raise ValueError("API key is missing. Please set AGENTROUTER_API_KEY or OPENROUTER_API_KEY in environment or sidebar.")

    clean_base_url = resolve_base_url(api_key, base_url)
    default_headers = {
        "HTTP-Referer": "https://mandea-ai.railway.app",
        "X-Title": "Mandea AI"
    }
    return OpenAI(
        api_key=api_key,
        base_url=clean_base_url,
        default_headers=default_headers,
        timeout=timeout,
        max_retries=1
    )

def is_html_response(text: str) -> bool:
    """
    Checks if a given string response is an HTML page (e.g. WAF block page or web portal) rather than valid LLM output.
    """
    if not text or not isinstance(text, str):
        return False
    lower = text.strip().lower()
    return lower.startswith("<!doctype") or lower.startswith("<html") or "<head>" in lower or "<body" in lower

def extract_response_text(resp_obj) -> str:
    """
    Safely extracts response string from various response formats (OpenAI object, dict, string).
    Detects and rejects HTML WAF/portal responses.
    """
    res_text = ""
    if isinstance(resp_obj, str):
        res_text = resp_obj
    elif isinstance(resp_obj, dict):
        choices = resp_obj.get('choices', [])
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get('message', {})
            if isinstance(msg, dict):
                res_text = msg.get('content', '') or msg.get('reasoning_content', '')
            elif isinstance(msg, str):
                res_text = msg
        else:
            res_text = resp_obj.get('content', '')
    elif hasattr(resp_obj, 'choices') and resp_obj.choices:
        choice = resp_obj.choices[0]
        msg = getattr(choice, 'message', None)
        if msg:
            content = getattr(msg, 'content', None)
            reasoning = getattr(msg, 'reasoning_content', None)
            res_text = content or reasoning or ""
    else:
        res_text = str(resp_obj) if resp_obj is not None else ""

    if is_html_response(res_text):
        return ""

    return res_text

def stream_response_generator(response):
    """
    Generator that safely extracts text deltas and reasoning content from API streaming response chunks.
    Detects HTML pages returned by web servers/WAFs and handles them gracefully.
    """
    try:
        if isinstance(response, str):
            if is_html_response(response):
                yield "⚠️ **API Error:** The selected Base API URL returned a Web/WAF HTML page instead of an API response. Please verify your Base API URL (e.g. `https://agentrouter.ai/v1` or `https://openrouter.ai/api/v1`) and API Key."
            else:
                yield response
            return

        for chunk in response:
            if isinstance(chunk, str):
                if is_html_response(chunk):
                    yield "⚠️ **API Error:** Received an HTML response page from the API gateway. Please check your Base API URL and credentials."
                    return
                yield chunk
                continue

            choices = getattr(chunk, 'choices', None)
            if choices is None and isinstance(chunk, dict):
                choices = chunk.get('choices', [])

            if choices:
                choice = choices[0]
                delta = getattr(choice, 'delta', None)
                if delta is None and isinstance(choice, dict):
                    delta = choice.get('delta', {})

                if delta:
                    content = getattr(delta, 'content', None)
                    if content is None and isinstance(delta, dict):
                        content = delta.get('content')

                    reasoning_content = getattr(delta, 'reasoning_content', None)
                    if reasoning_content is None and isinstance(delta, dict):
                        reasoning_content = delta.get('reasoning_content')

                    target_text = content or reasoning_content
                    if target_text:
                        if is_html_response(target_text):
                            yield "⚠️ **API Error:** The server returned an HTML error page instead of text."
                            return
                        yield target_text
    except Exception as e:
        yield f"\n\n⚠️ *[Stream Error]: {str(e)}*"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_available_models(api_key: str, base_url: str = "") -> list[str]:
    """
    Fetches the list of models from AgentRouter / OpenRouter API with 1-hour caching.
    Falls back to a default list containing Agent Router specific models if unreachable.
    """
    default_models = [
        "glm-5.3",
        "deepseek-v4-flash",
        "claude-opus-5",
        "claude-opus-4-8",
        "gpt-5.6-sol",
        "claude-fable-5",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "claude-3-haiku",
        "deepseek/deepseek-chat"
    ]
    if not api_key:
        return default_models

    resolved_url = resolve_base_url(api_key, base_url)
    try:
        clean_url = f"{resolved_url}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(clean_url, headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and isinstance(data["data"], list):
                models = [m["id"] for m in data["data"] if "id" in m]
                if models:
                    return sorted(models)
    except Exception:
        pass

    return default_models

def prepare_messages_for_api(chat_history: list[dict], attached_files: list[dict], user_prompt: str) -> list[dict]:
    """
    Formats messages for the chat completion request, including multi-modal image content and document context.
    """
    formatted_messages = []

    doc_contexts = []
    image_contents = []

    for file_info in attached_files:
        if file_info["file_type"] == "document":
            doc_contexts.append(f"--- Document File: {file_info['filename']} ---\n{file_info['content']}\n")
        elif file_info["file_type"] == "image":
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": file_info["content"]
                }
            })

    for msg in chat_history:
        formatted_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    user_content_parts = []

    if doc_contexts:
        doc_prompt = "The user attached the following documents:\n\n" + "\n".join(doc_contexts)
        user_content_parts.append({"type": "text", "text": doc_prompt})

    if user_prompt:
        user_content_parts.append({"type": "text", "text": user_prompt})

    for img in image_contents:
        user_content_parts.append(img)

    if not user_content_parts:
        user_content_parts.append({"type": "text", "text": "Analyzing attached inputs."})

    has_images = any(p.get("type") == "image_url" for p in user_content_parts)
    if not has_images:
        combined_text = "\n\n".join(p["text"] for p in user_content_parts if p.get("type") == "text")
        formatted_messages.append({"role": "user", "content": combined_text})
    else:
        formatted_messages.append({"role": "user", "content": user_content_parts})

    return formatted_messages
