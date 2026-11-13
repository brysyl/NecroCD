"""libcst transformers: legacy imports/calls -> modern, plus code generators."""
from __future__ import annotations

import hashlib
import re

import libcst as cst

from models import TransformStep
from parser.ast_analyzer import list_functions

IMPORT_RENAMES = {
    "Queue": "queue",
    "ConfigParser": "configparser",
    "cPickle": "pickle",
    "Tkinter": "tkinter",
    "httplib": "http.client",
    "SocketServer": "socketserver",
    "urlparse": "urllib.parse",
}
CALL_RENAMES = {
    "xrange": "range",
    "raw_input": "input",
    "unicode": "str",
    "unichr": "chr",
    "os.getcwdu": "os.getcwd",
    "time.clock": "time.perf_counter",
    "base64.encodestring": "base64.encodebytes",
    "base64.decodestring": "base64.decodebytes",
}


def _dotted_to_node(name: str) -> cst.BaseExpression:
    parts = name.split(".")
    node: cst.BaseExpression = cst.Name(parts[0])
    for p in parts[1:]:
        node = cst.Attribute(value=node, attr=cst.Name(p))
    return node


def _node_to_dotted(node: cst.CSTNode) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        base = _node_to_dotted(node.value)
        return f"{base}.{node.attr.value}" if base else ""
    return ""


class LegacyModernizer(cst.CSTTransformer):
    def __init__(self) -> None:
        self.applied: list[TransformStep] = []

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        names = []
        changed = False
        for alias in updated_node.names:
            dotted = _node_to_dotted(alias.name)
            if dotted in IMPORT_RENAMES:
                new = IMPORT_RENAMES[dotted]
                # alias to the old name so existing usages keep working
                asname = alias.asname or cst.AsName(name=cst.Name(dotted))
                alias = alias.with_changes(name=_dotted_to_node(new), asname=asname)
                self.applied.append(TransformStep(kind="replace-import", target=dotted, replacement=new))
                changed = True
            names.append(alias)
        return updated_node.with_changes(names=names) if changed else updated_node

    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
        if updated_node.module is None or updated_node.relative:
            return updated_node
        dotted = _node_to_dotted(updated_node.module)
        if dotted in IMPORT_RENAMES:
            new = IMPORT_RENAMES[dotted]
            self.applied.append(TransformStep(kind="replace-import", target=dotted, replacement=new))
            return updated_node.with_changes(module=_dotted_to_node(new))
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        name = _node_to_dotted(updated_node.func)
        if name in CALL_RENAMES:
            new = CALL_RENAMES[name]
            self.applied.append(TransformStep(kind="replace-call", target=name, replacement=new))
            return updated_node.with_changes(func=_dotted_to_node(new))
        return updated_node


def modernize(source: str) -> tuple[str, list[TransformStep]]:
    """Apply the legacy modernizer. Raises libcst.ParserSyntaxError on bad source."""
    module = cst.parse_module(source)
    t = LegacyModernizer()
    new = module.visit(t)
    return new.code, t.applied


def source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def generate_router(source: str, prefix: str = "legacy") -> str:
    """Generate a FastAPI router exposing top-level legacy functions as POST endpoints."""
    funcs = [f for f in list_functions(source) if not f["name"].startswith("_")]
    lines = [
        "from fastapi import APIRouter",
        "from pydantic import BaseModel",
        "",
        f'router = APIRouter(prefix="/{prefix}", tags=["{prefix}"])',
        "",
    ]
    for f in funcs:
        cls = "".join(w.capitalize() for w in f["name"].split("_")) + "Request"
        lines.append(f"class {cls}(BaseModel):")
        if f["params"]:
            lines.extend(f"    {p}: object = None" for p in f["params"])
        else:
            lines.append("    pass")
        lines += [
            "",
            "",
            f'@router.post("/{f["name"]}")',
            f"async def {f['name']}_endpoint(body: {cls}) -> dict:",
            f'    """Resurrected from legacy {f["name"]}()."""',
            f'    return {{"function": "{f["name"]}", "args": body.model_dump()}}',
            "",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def generate_component(source: str, name: str = "Resurrected") -> str:
    """Generate a TypeScript/Next.js client component stub listing the functions."""
    name = re.sub(r"\W", "", name.title()) or "Resurrected"
    funcs = [f["name"] for f in list_functions(source) if not f["name"].startswith("_")]
    items = "\n".join(f'        <li key="{n}">{n}</li>' for n in funcs)
    return (
        "'use client';\n\n"
        f"export default function {name}Panel() {{\n"
        "  return (\n"
        "    <section>\n"
        "      <ul>\n"
        f"{items}\n"
        "      </ul>\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )
