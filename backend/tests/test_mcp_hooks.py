import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mcp_tools_and_allowlist(monkeypatch, tmp_path):
    mcp = _load(ROOT / "mcp" / "server.py", "necrocd_mcp")
    monkeypatch.setenv("NECROCD_ALLOWED_ROOTS", str(ROOT))
    names = {t["name"] for t in mcp.list_tools()}
    assert {"git_list_refs", "git_write_ref", "docker_logs"} <= names
    resp = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "git_list_refs", "arguments": {"repo": str(tmp_path)}}})
    assert resp["result"]["isError"]
    bad = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "docker_logs", "arguments": {"container": "x; rm -rf /"}}})
    assert bad["result"]["isError"]


def test_precommit_hook_reports(tmp_path):
    def g(*a):
        return subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True, text=True)
    g("init", "-b", "main")
    (tmp_path / "x.py").write_text("import urllib2\n")
    g("add", "x.py")
    r = subprocess.run([sys.executable, str(ROOT / ".kiro/hooks/pre-commit-exorcism.py")],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0
    assert "urllib2" in r.stdout
