import ast

class SecurityASTVisitor(ast.NodeVisitor):
    def __init__(self, filename: str = ""):
        self.filename = filename
        self.findings = []

    def visit_Call(self, node):
        # Detect eval() and exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                line = getattr(node, "lineno", "?")
                self.findings.append(f"🔴 [{self.filename}:{line}] Critical: Call to dangerous built-in function '{node.func.id}()'")

        # Detect subprocess with shell=True
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("Popen", "run", "call", "check_output"):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        line = getattr(node, "lineno", "?")
                        self.findings.append(f"⚠️ [{self.filename}:{line}] High: Subprocess command executed with shell=True")

        self.generic_visit(node)

    def visit_Assign(self, node):
        # Detect hardcoded secret assignments (e.g., api_key = "sk-...")
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                if any(sec in var_name for sec in ["secret", "api_key", "password", "token", "auth"]):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        if len(val) > 8:
                            line = getattr(node, "lineno", "?")
                            self.findings.append(f"🔑 [{self.filename}:{line}] Medium: Hardcoded secret assignment in variable '{target.id}'")

        self.generic_visit(node)

def analyze_python_ast(code: str, filename: str = "code.py") -> list[str]:
    """
    Performs AST analysis on Python source code.
    Returns a list of structured security finding messages.
    """
    if not code.strip():
        return []

    try:
        tree = ast.parse(code, filename=filename)
        visitor = SecurityASTVisitor(filename)
        visitor.visit(tree)
        return visitor.findings
    except SyntaxError as e:
        return [f"⚠️ [{filename}:{e.lineno}] SyntaxError during AST parsing: {e.msg}"]
    except Exception as e:
        return [f"⚠️ [{filename}] Error during AST parsing: {str(e)}"]
