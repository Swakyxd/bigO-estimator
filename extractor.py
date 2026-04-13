"""
Function extractor for batch file analysis.
Supports Python (.py) and C/C++ (.cpp, .c, .h) source files.
"""

import ast
import re
from pathlib import Path


# ── Python extraction ──────────────────────────────────────────────────────────

def _extract_python_functions(source: str) -> list[dict]:
    """
    Use the AST to extract top-level and class-level function definitions.
    Returns list of {"name": str, "code": str}.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [{"name": "__parse_error__", "code": f"# SyntaxError: {e}\n{source[:200]}"}]

    lines = source.splitlines(keepends=True)
    results = []

    def _node_source(node) -> str:
        start = node.lineno - 1
        end = node.end_lineno
        return "".join(lines[start:end])

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            code = _node_source(node)
            results.append({"name": node.name, "code": code.strip()})

    # De-duplicate by name (keep first occurrence)
    seen = set()
    unique = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    return unique


# ── C/C++ extraction ───────────────────────────────────────────────────────────

# Regex to match C/C++ function definitions (not declarations)
_CPP_FUNC_RE = re.compile(
    r"""
    (?:^|\n)                         # start of line
    (?:[\w:<>*&\s]+?\s+)?           # optional return type tokens
    (?P<name>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)   # function name (allows Cls::method)
    \s*\(                            # opening paren
    [^)]*                            # parameter list
    \)\s*                            # closing paren + ws
    (?:const\s*)?                    # optional const
    (?:noexcept\s*)?                 # optional noexcept
    \{                               # opening brace
    """,
    re.VERBOSE | re.MULTILINE,
)


def _extract_cpp_functions(source: str) -> list[dict]:
    """
    Heuristic C/C++ function extractor using brace-matching.
    """
    results = []
    seen: set[str] = set()

    for m in _CPP_FUNC_RE.finditer(source):
        name = m.group("name")
        if name in ("if", "else", "for", "while", "switch", "do", "catch", "struct", "class"):
            continue

        # Walk forward from the opening brace to find the matching close brace
        start_idx = m.end() - 1  # position of '{'
        depth = 0
        end_idx = start_idx
        for i in range(start_idx, len(source)):
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break

        code = source[m.start():end_idx].strip()

        if name not in seen:
            seen.add(name)
            results.append({"name": name, "code": code})

    return results


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_functions(filename: str, source: str) -> list[dict]:
    """
    Extract functions from source text.

    Args:
        filename: Original filename (used to detect language).
        source:   Full source code as a string.

    Returns:
        list of {"name": str, "code": str}
    """
    ext = Path(filename).suffix.lower()
    if ext == ".py":
        return _extract_python_functions(source)
    elif ext in (".cpp", ".c", ".h", ".cc", ".cxx"):
        return _extract_cpp_functions(source)
    else:
        # Fallback: treat entire file as one chunk
        return [{"name": "<full file>", "code": source}]
