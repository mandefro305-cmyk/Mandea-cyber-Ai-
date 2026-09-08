import json

def export_chat_to_markdown(messages: list[dict], title: str = "Chat Session Export") -> str:
    """
    Exports chat message history into formatted Markdown string.
    """
    md = [f"# {title}\n"]
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        md.append(f"### 👤 {role if role=='User' else '🤖 Assistant'}")
        md.append(f"{content}\n")
    return "\n".join(md)

def export_chat_to_json(messages: list[dict]) -> str:
    """
    Exports chat message history into JSON string.
    """
    return json.dumps(messages, indent=2)
