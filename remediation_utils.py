import re

def generate_remediation_diff(filename: str, original_code: str, findings: list[str]) -> str:
    """
    Generates suggested secure code replacements and git patch diffs for common vulnerabilities.
    """
    if not original_code or not findings:
        return ""

    lines = original_code.splitlines()
    modified_lines = list(lines)
    changes_made = False

    for idx, line in enumerate(lines):
        # Fix eval()
        if re.search(r'\beval\s*\(', line):
            modified_lines[idx] = f"# FIX: Replaced unsafe eval() with safe evaluation/parsing\n# {line}\n# TODO: Use ast.literal_eval() or explicit logic"
            changes_made = True

        # Fix exec()
        if re.search(r'\bexec\s*\(', line):
            modified_lines[idx] = f"# FIX: Removed unsafe exec()\n# {line}"
            changes_made = True

        # Fix SQL Injection string concat
        if re.search(r'(?i)(SELECT|INSERT|UPDATE|DELETE).*\+.*|\bexecute\s*\(\s*["\'].*%', line):
            modified_lines[idx] = f"# FIX: Parameterized SQL Query to prevent SQL Injection\n# BEFORE: {line}\n# db.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
            changes_made = True

        # Fix subprocess shell=True
        if re.search(r'(?i)subprocess\.(Popen|run|call)\s*\([^)]*shell\s*=\s*True', line):
            modified_lines[idx] = line.replace("shell=True", "shell=False # Safe execution without shell")
            changes_made = True

        # Fix verify=False
        if re.search(r'(?i)verify\s*=\s*False', line):
            modified_lines[idx] = line.replace("verify=False", "verify=True # Enforce SSL TLS verification")
            changes_made = True

    if not changes_made:
        return "# No automated diff patch rule matched for these findings."

    # Build unified diff representation
    diff_output = [f"--- a/{filename}", f"+++ b/{filename}"]
    for orig, mod in zip(lines, modified_lines):
        if orig != mod:
            diff_output.append(f"- {orig}")
            diff_output.append(f"+ {mod}")
        else:
            diff_output.append(f"  {orig}")

    return "\n".join(diff_output)
