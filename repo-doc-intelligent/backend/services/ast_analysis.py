import ast
import re
from typing import Optional

try:
    from tree_sitter_languages import get_parser, get_language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

EXT_TO_TS_LANG = {
    "js": "javascript",
    "ts": "typescript",
    "java": "java",
    "go": "go",
    "c": "c",
    "cpp": "cpp",
    "rs": "rust",
}


def _py_collect_calls_in_scope(node: ast.AST, caller: str, symbol_calls: list) -> None:
    """Collect (caller, callee) for every Call in node's body. caller is function name or Class.method."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                symbol_calls.append((caller, n.func.id))
            elif isinstance(n.func, ast.Attribute):
                symbol_calls.append((caller, n.func.attr))


def _py_analyze(content: str):
    classes = []
    functions = []
    methods = []
    imports = []
    calls = []
    symbol_calls: list = []
    has_main_guard = False
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"classes": classes, "functions": functions, "methods": methods, "imports": imports, "calls": calls, "symbol_calls": symbol_calls, "has_main_guard": has_main_guard}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    methods.append(f"{node.name}.{child.name}")
                    _py_collect_calls_in_scope(child, f"{node.name}.{child.name}", symbol_calls)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            else:
                mod = node.module or ""
                imports.append(mod.split(".")[0])
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            if (isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__" and
                    isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == "__main__"):
                has_main_guard = True
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            _py_collect_calls_in_scope(node, node.name, symbol_calls)
    return {"classes": classes, "functions": functions, "methods": methods, "imports": imports, "calls": calls, "symbol_calls": symbol_calls, "has_main_guard": has_main_guard}


def _regex_fallback(content: str):
    classes = []
    functions = []
    methods = []
    imports = []
    calls = []
    for m in re.finditer(r"\bclass\s+(\w+)\b", content):
        classes.append(m.group(1))
    for m in re.finditer(r"\bdef\s+(\w+)\s*\(", content):
        functions.append(m.group(1))
    for m in re.finditer(r"\b(?:import|from)\s+([\w.]+)", content):
        imports.append(m.group(1).split(".")[0])
    for m in re.finditer(r"\b(?:function|func)\s+(\w+)\s*\(", content):
        functions.append(m.group(1))
    for m in re.finditer(r"\b(?:require|import)\s*\(\s*['\"]([^'\"]+)['\"]", content):
        imports.append(m.group(1).split("/")[0])
    for m in re.finditer(r"\b(\w+)\s*\(", content):
        cand = m.group(1)
        if cand not in ("if", "for", "while", "with", "def", "class", "return", "yield", "lambda"):
            calls.append(cand)
    return {"classes": classes, "functions": functions, "methods": methods, "imports": imports, "calls": list(dict.fromkeys(calls)), "symbol_calls": [], "has_main_guard": False}


def _ts_walk(node, source_bytes, lang, results, current_symbol: str = ""):
    kind = node.type
    if kind in ("class_declaration", "class_definition"):
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            results["classes"].append(class_name)
            for child in node.children:
                if child.type in ("method_definition", "function_definition"):
                    mn = child.child_by_field_name("name")
                    if mn:
                        method_name = source_bytes[mn.start_byte:mn.end_byte].decode("utf-8", errors="replace")
                        results["methods"].append(class_name + "." + method_name)
                        prev = current_symbol
                        _ts_walk(child, source_bytes, lang, results, class_name + "." + method_name)
                        continue
    if kind in ("function_definition", "function_declaration", "method_definition", "arrow_function"):
        name_node = node.child_by_field_name("name")
        name = ""
        if name_node:
            name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
            if kind != "method_definition":
                results["functions"].append(name)
        sym = name or current_symbol
        if sym:
            for child in node.children:
                _ts_walk(child, source_bytes, lang, results, sym)
            return
    if "import" in kind or kind == "import_statement":
        for child in node.children:
            if child.type == "identifier" or child.type == "string":
                text = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip("'\"")
                if text and not text.startswith("."):
                    results["imports"].append(text.split("/")[0].split(".")[0])
    if kind in ("call_expression", "call") and current_symbol:
        fn = node.child_by_field_name("function")
        if fn:
            callee = ""
            if fn.type == "identifier":
                callee = source_bytes[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
            elif fn.type == "member_expression" or fn.type == "field_expression":
                member = fn.child_by_field_name("property") or fn.children[-1]
                if member:
                    callee = source_bytes[member.start_byte:member.end_byte].decode("utf-8", errors="replace")
            if callee:
                results["calls"].append(callee)
                results["symbol_calls"].append((current_symbol, callee))
    for child in node.children:
        _ts_walk(child, source_bytes, lang, results, current_symbol)


def _tree_sitter_analyze(content: str, lang: str):
    if not TREE_SITTER_AVAILABLE or lang not in EXT_TO_TS_LANG.values():
        return _regex_fallback(content)
    try:
        parser = get_parser(lang)
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)
        results = {"classes": [], "functions": [], "methods": [], "imports": [], "calls": [], "symbol_calls": [], "has_main_guard": False}
        _ts_walk(tree.root_node, source_bytes, lang, results)
        return results
    except Exception:
        return _regex_fallback(content)


def analyze_file(rel_path: str, content: Optional[str]) -> dict:
    if not content:
        return {"classes": [], "functions": [], "methods": [], "imports": [], "calls": [], "symbol_calls": [], "has_main_guard": False}
    ext = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
    if ext == "py":
        return _py_analyze(content)
    ts_lang = EXT_TO_TS_LANG.get(ext)
    if ts_lang:
        return _tree_sitter_analyze(content, ts_lang)
    return _regex_fallback(content)
