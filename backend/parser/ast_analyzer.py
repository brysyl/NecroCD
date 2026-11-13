"""Detect legacy imports, deprecated calls, syntax rot and security risks."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import libcst as cst

from models import Finding

LEGACY_IMPORTS: dict[str, str] = {
    "urllib2": "httpx",
    "urllib.urlencode": "urllib.parse.urlencode",
    "Queue": "queue",
    "ConfigParser": "configparser",
    "StringIO": "io.StringIO",
    "cPickle": "pickle",
    "Tkinter": "tkinter",
    "httplib": "http.client",
    "urlparse": "urllib.parse",
    "SocketServer": "socketserver",
    "commands": "subprocess",
    "imp": "importlib",
    "distutils": "setuptools",
}

DEPRECATED_CALLS: dict[str, str] = {
    "os.getcwdu": "os.getcwd",
    "string.letters": "string.ascii_letters",
    "time.clock": "time.perf_counter",
    "asyncio.coroutine": "async def",
    "inspect.getargspec": "inspect.getfullargspec",
    "platform.linux_distribution": "distro.name",
    "base64.encodestring": "base64.encodebytes",
    "base64.decodestring": "base64.decodebytes",
    "xrange": "range",
    "raw_input": "input",
    "unicode": "str",
    "unichr": "chr",
    "basestring": "str",
}

SECURITY_CALLS: dict[str, tuple[str, str]] = {
    "eval": ("high", "eval() executes arbitrary code"),
    "exec": ("high", "exec() executes arbitrary code"),
    "pickle.loads": ("high", "unpickling untrusted data is unsafe"),
    "pickle.load": ("high", "unpickling untrusted data is unsafe"),
    "os.system": ("high", "os.system enables shell injection"),
    "yaml.load": ("medium", "use yaml.safe_load"),
    "hashlib.md5": ("low", "md5 is cryptographically broken"),
    "input": ("info", "input() is py2 eval-like on legacy code"),
}

_PY2_PRINT = re.compile(r"^\s*print\s+[^\s(=].*$")
_PY2_EXCEPT = re.compile(r"^\s*except\s+[\w.]+\s*,\s*\w+\s*:")
_PY2_BACKTICK_OR_NE = re.compile(r"<>")


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _syntax_rot_from_text(source: str, file: str) -> list[Finding]:
    out: list[Finding] = []
    for i, line in enumerate(source.splitlines(), 1):
        if _PY2_PRINT.match(line):
            out.append(Finding(rule="syntax-rot", severity="high", file=file, line=i,
                               message="Python 2 print statement", symbol="print",
                               suggestion="print(...)"))
        elif _PY2_EXCEPT.match(line):
            out.append(Finding(rule="syntax-rot", severity="high", file=file, line=i,
                               message="Python 2 except syntax", suggestion="except X as e:"))
        elif _PY2_BACKTICK_OR_NE.search(line):
            out.append(Finding(rule="syntax-rot", severity="medium", file=file, line=i,
                               message="Python 2 <> operator", suggestion="!="))
    return out


def analyze_source(source: str, file: str = "<memory>") -> list[Finding]:
    """Analyze python source and return findings. Never raises on bad syntax."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        found = _syntax_rot_from_text(source, file)
        if not found:
            found.append(Finding(rule="syntax-rot", severity="high", file=file,
                                 line=exc.lineno or 0,
                                 message=f"Unparseable source: {exc.msg}"))
        return found
    except (ValueError, RecursionError) as exc:
        return [Finding(rule="syntax-rot", severity="high", file=file, message=f"Unparseable source: {exc}")]

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in LEGACY_IMPORTS:
                    findings.append(Finding(rule="legacy-import", severity="medium", file=file,
                                            line=node.lineno, symbol=alias.name,
                                            message=f"Legacy module '{alias.name}'",
                                            suggestion=LEGACY_IMPORTS[root]))
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in LEGACY_IMPORTS and node.level == 0:
                findings.append(Finding(rule="legacy-import", severity="medium", file=file,
                                        line=node.lineno, symbol=node.module,
                                        message=f"Legacy module '{node.module}'",
                                        suggestion=LEGACY_IMPORTS[root]))
        elif isinstance(node, (ast.Call, ast.Attribute, ast.Name)):
            name = _dotted(node.func) if isinstance(node, ast.Call) else ""
            if isinstance(node, ast.Call) and name:
                if name in DEPRECATED_CALLS:
                    findings.append(Finding(rule="deprecated-call", severity="medium", file=file,
                                            line=node.lineno, symbol=name,
                                            message=f"Deprecated call '{name}'",
                                            suggestion=DEPRECATED_CALLS[name]))
                if name in SECURITY_CALLS:
                    sev, msg = SECURITY_CALLS[name]
                    if name != "input":
                        findings.append(Finding(rule="security-risk", severity=sev, file=file,
                                                line=node.lineno, symbol=name, message=msg))
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append(Finding(rule="security-risk", severity="high", file=file,
                                                line=node.lineno, symbol=name,
                                                message="subprocess with shell=True"))
    return findings


def analyze_file(path: Path, root: Path | None = None) -> list[Finding]:
    rel = str(path.relative_to(root)) if root else str(path)
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [Finding(rule="syntax-rot", severity="low", file=rel, message=f"Unreadable: {exc}")]
    return analyze_source(source, rel)


def analyze_tree(root: Path) -> list[Finding]:
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
    out: list[Finding] = []
    for p in sorted(root.rglob("*.py")):
        if skip.intersection(p.relative_to(root).parts):
            continue
        out.extend(analyze_file(p, root))
    return out


def list_functions(source: str) -> list[dict]:
    """Map top-level functions using libcst (positions-free, formatting safe)."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return []
    funcs = []
    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            params = [p.name.value for p in stmt.params.params]
            funcs.append({"name": stmt.name.value, "params": params, "async": stmt.asynchronous is not None})
    return funcs
