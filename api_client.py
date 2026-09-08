import os
import requests
from openai import OpenAI

def get_agentrouter_client(api_key: str, base_url: str, timeout: float = 120.0):
    """
    Creates an OpenAI-compatible client for AgentRouter / OpenRouter with configurable timeout and retries.
    """
    if not api_key:
        raise ValueError("API key is missing. Please set AGENTROUTER_API_KEY or OPENROUTER_API_KEY in environment or sidebar.")

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=2
    )

def fetch_available_models(api_key: str, base_url: str) -> list[str]:
    """
    Fetches the list of models from AgentRouter / OpenRouter API.
    Falls back to a default list if the endpoint is unreachable.
    """
    default_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "claude-3-haiku",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.1-70b-instruct"
    ]
    if not api_key:
        return default_models

    try:
        url = f"{base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(url, headers=headers, timeout=5)
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

    # Insert document attachments into system context or user message
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

    # Historical messages
    for msg in chat_history:
        formatted_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Build user message content
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

    # If user_content_parts only has text and no images, we can send content as string
    has_images = any(p.get("type") == "image_url" for p in user_content_parts)
    if not has_images:
        combined_text = "\n\n".join(p["text"] for p in user_content_parts if p.get("type") == "text")
        formatted_messages.append({"role": "user", "content": combined_text})
    else:
        formatted_messages.append({"role": "user", "content": user_content_parts})

    return formatted_messages
