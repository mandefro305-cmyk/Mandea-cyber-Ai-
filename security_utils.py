import re

COMMON_SENSITIVE_PATTERNS = [
    # API Keys & Secrets
    (re.compile(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{16,})["\']?'), r'\1: "[REDACTED_API_KEY]"'),
    # Generic Tokens (e.g. Bearer eyJ...)
    (re.compile(r'Bearer\s+([a-zA-Z0-9_\-\.]{20,})'), r'Bearer [REDACTED_TOKEN]'),
    # Private Keys
    (re.compile(r'-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PRIVATE)\s+KEY-----[\s\S]*?-----END\s+\1\s+KEY-----'), r'[REDACTED_PRIVATE_KEY]'),
    # Emails
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), r'[REDACTED_EMAIL]'),
    # Credit Card Numbers (13-19 digits)
    (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), r'[REDACTED_CREDIT_CARD]')
]

CODE_SECURITY_PATTERNS = [
    (re.compile(r'(?i)(SELECT|INSERT|UPDATE|DELETE).*\+.*|\bexecute\s*\(\s*["\'].*%'), "Potential SQL Injection: Direct string concatenation in SQL query."),
    (re.compile(r'(?i)\beval\s*\('), "Critical: Use of eval() can allow arbitrary code execution."),
    (re.compile(r'(?i)\bexec\s*\('), "Critical: Use of exec() can allow arbitrary code execution."),
    (re.compile(r'(?i)innerHTML\s*='), "Potential XSS: Assigning user input directly to innerHTML."),
    (re.compile(r'(?i)subprocess\.(Popen|run|call)\s*\([^)]*shell\s*=\s*True'), "Potential Command Injection: Running shell commands with shell=True."),
    (re.compile(r'(?i)verify\s*=\s*False'), "Insecure TLS/SSL: Certificate verification is disabled (verify=False)."),
    (re.compile(r'(?i)(md5|sha1)\b'), "Weak Cryptography: MD5/SHA1 are weak hashing algorithms.")
]

def redact_sensitive_data(text: str) -> tuple[str, int]:
    """
    Redacts sensitive credentials, tokens, PII from text.
    Returns (redacted_text, redaction_count)
    """
    if not text:
        return text, 0

    redacted = text
    count = 0
    for pattern, replacement in COMMON_SENSITIVE_PATTERNS:
        matches = pattern.findall(redacted)
        if matches:
            count += len(matches)
            redacted = pattern.sub(replacement, redacted)

    return redacted, count

def scan_code_for_vulnerabilities(code_text: str, filename: str = "") -> list[str]:
    """
    Scans code text against security rule heuristics and returns identified warnings.
    """
    if not code_text:
        return []

    warnings = []
    lines = code_text.splitlines()

    for idx, line in enumerate(lines, 1):
        for pattern, warning_msg in CODE_SECURITY_PATTERNS:
            if pattern.search(line):
                loc = f"Line {idx}" if not filename else f"{filename}:{idx}"
                warnings.append(f"⚠️ [{loc}] {warning_msg}")

    return warnings
