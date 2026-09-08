SYSTEM_PRESETS = {
    "General Assistant": "You are a helpful, accurate, and concise AI assistant.",
    "Code Auditor & Security Specialist": (
        "You are an expert security auditor and senior software engineer. "
        "Review code thoroughly for bugs, performance issues, logic flaws, and security vulnerabilities "
        "(such as OWASP Top 10 vulnerabilities like SQL Injection, XSS, CSRF, insecure deserialization, "
        "and unhandled edge cases). Provide clear explanation of risks and secure remediations with code examples."
    ),
    "Document Summarizer": (
        "You are an expert document analyst. Extract key takeaways, bullet points, action items, "
        "and executive summaries from provided documents concisely and structured cleanly."
    ),
    "Technical Writer": (
        "You are a professional technical writer. Help format technical documentation, API specs, "
        "and user guides clearly using clean Markdown."
    ),
    "Data Analyst": (
        "You are an expert data scientist and analyst. Help analyze data distributions, identify trends, "
        "and provide statistical insights and clean visualizations recommendations."
    )
}

MODEL_PRICING_PER_1K = {
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "deepseek/deepseek-chat": {"input": 0.00014, "output": 0.00028},
}

def estimate_tokens(text: str) -> int:
    """Rough estimation: ~4 chars per token for English/Code."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    for key, price in MODEL_PRICING_PER_1K.items():
        if key in model_name.lower():
            in_cost = (input_tokens / 1000.0) * price["input"]
            out_cost = (output_tokens / 1000.0) * price["output"]
            return round(in_cost + out_cost, 6)
    # Default fallback rate
    return round((input_tokens + output_tokens) / 1000.0 * 0.002, 6)
