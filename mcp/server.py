"""NecroCD local MCP server (stdio, JSON-RPC 2.0, newline-delimited).

Tools: git_list_refs, git_read_ref, git_write_ref, docker_logs.
Git access is restricted to roots in NECROCD_ALLOWED_ROOTS (os.pathsep separated).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROTOCOL = "2024-11-05"
REF_RE = re.compile(r"^refs/(heads|tags|necrocd)/[A-Za-z0-9._/-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CONTAINER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ToolError(Exception):
    pass


def allowed_roots() -> list[Path]:
    raw = os.environ.get("NECROCD_ALLOWED_ROOTS") or str(Path(__file__).resolve().parents[1])
    return [Path(p).resolve() for p in raw.split(os.pathsep) if p]


def resolve_repo(path: str) -> Path:
    p = Path(path).resolve()
    if not any(p == r or r in p.parents for r in allowed_roots()):
        raise ToolError(f"Path outside allowlisted roots: {path}")
    if not (p / ".git").exists():
        raise ToolError(f"Not a git repository: {path}")
    return p


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise ToolError(r.stderr.strip() or "git failed")
    return r.stdout


def _check_ref(ref: str) -> str:
    if ".." in ref or not REF_RE.match(ref):
        raise ToolError("Invalid ref (must match refs/heads|tags|necrocd/...)")
    return ref


def git_list_refs(repo: str) -> str:
    return _git(resolve_repo(repo), "for-each-ref", "--format=%(refname) %(objectname)")


def git_read_ref(repo: str, ref: str) -> str:
    return _git(resolve_repo(repo), "rev-parse", "--verify", _check_ref(ref)).strip()


def git_write_ref(repo: str, ref: str, sha: str) -> str:
    if not SHA_RE.match(sha):
        raise ToolError("sha must be a full 40-char lowercase hex object id")
    r = resolve_repo(repo)
    _git(r, "cat-file", "-e", f"{sha}^{{commit}}")
    _git(r, "update-ref", _check_ref(ref), sha)
    return f"{ref} -> {sha}"


def docker_logs(container: str, tail: int = 200) -> str:
    if not CONTAINER_RE.match(container):
        raise ToolError("Invalid container name")
    tail = max(1, min(int(tail), 2000))
    try:
        r = subprocess.run(["docker", "logs", "--tail", str(tail), container],
                           capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ToolError(f"Docker unavailable: {exc}")
    if r.returncode != 0:
        raise ToolError(r.stderr.strip() or "docker logs failed")
    return r.stdout + r.stderr


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": {k: {"type": t} for k, t in props.items()}, "required": required}


TOOLS = {
    "git_list_refs": (git_list_refs, "List git refs in an allowlisted repo", _schema({"repo": "string"}, ["repo"])),
    "git_read_ref": (git_read_ref, "Resolve a ref to a sha", _schema({"repo": "string", "ref": "string"}, ["repo", "ref"])),
    "git_write_ref": (git_write_ref, "Point a ref at an existing commit",
                      _schema({"repo": "string", "ref": "string", "sha": "string"}, ["repo", "ref", "sha"])),
    "docker_logs": (docker_logs, "Read container logs (read only)",
                    _schema({"container": "string", "tail": "integer"}, ["container"])),
}


def list_tools() -> list[dict]:
    return [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]


def handle(msg: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # notification
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "necrocd-mcp", "version": "0.1.0"}}
    elif method == "tools/list":
        result = {"tools": list_tools()}
    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        try:
            text = TOOLS[name][0](**params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": text}]}
        except ToolError as exc:
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except TypeError as exc:
            result = {"content": [{"type": "text", "text": f"Bad arguments: {exc}"}], "isError": True}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = handle(json.loads(line))
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
