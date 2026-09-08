from duckduckgo_search import DDGS

def perform_web_search(query: str, max_results: int = 4) -> list[dict]:
    """
    Performs web search using DuckDuckGo and returns title, href, and snippet.
    """
    if not query.strip():
        return []

    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "href": item.get("href", ""),
                    "body": item.get("body", "")
                })
        return results
    except Exception as e:
        return [{"title": "Search Error", "href": "", "body": f"Failed to perform search: {str(e)}"}]

def format_search_context(search_results: list[dict]) -> str:
    if not search_results:
        return ""

    context_lines = ["--- Live Web Search Context ---"]
    for idx, res in enumerate(search_results, 1):
        context_lines.append(f"[{idx}] {res['title']}\nURL: {res['href']}\nSnippet: {res['body']}\n")

    return "\n".join(context_lines)
