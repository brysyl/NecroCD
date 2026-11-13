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


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _call(mcp, name, args):
    return mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}})["result"]


def test_mcp_ref_roundtrip_and_boundaries(monkeypatch, tmp_path):
    mcp = _load(ROOT / "mcp" / "server.py", "necrocd_mcp2")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "a.txt").write_text("a")
    _git(repo, "add", "a.txt")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "c")
    sha = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("NECROCD_ALLOWED_ROOTS", str(tmp_path))
    assert "refs/heads/main" in _call(mcp, "git_list_refs", {"repo": str(repo)})["content"][0]["text"]
    assert _call(mcp, "git_write_ref", {"repo": str(repo), "ref": "refs/necrocd/x", "sha": sha}).get("isError") is None
    assert _call(mcp, "git_read_ref", {"repo": str(repo), "ref": "refs/necrocd/x"})["content"][0]["text"] == sha
    # invalid refs / injection
    for bad in ["--delete", "refs/heads/../x", "HEAD", "refs/remotes/o/x", "refs/heads/a b"]:
        assert _call(mcp, "git_read_ref", {"repo": str(repo), "ref": bad})["isError"]
    assert _call(mcp, "git_write_ref", {"repo": str(repo), "ref": "refs/necrocd/y", "sha": "HEAD"})["isError"]
    # path escape via .. and symlink
    assert _call(mcp, "git_list_refs", {"repo": str(repo / ".." / "..")})["isError"]
    outside = tmp_path.parent / (tmp_path.name + "_outside")
    outside.mkdir()
    _git(outside, "init", "-b", "main")
    link = tmp_path / "link"
    link.symlink_to(outside)
    assert _call(mcp, "git_list_refs", {"repo": str(link)})["isError"]
    # stdio framing over a real subprocess
    import json
    p = subprocess.run([sys.executable, str(ROOT / "mcp" / "server.py")], capture_output=True, text=True,
                       input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
    assert len(json.loads(p.stdout)["result"]["tools"]) == 4


def test_mcp_config_valid():
    import json
    cfg = json.loads((ROOT / ".kiro/settings/mcp.json").read_text())["mcpServers"]["necrocd"]
    assert cfg["args"] == ["mcp/server.py"] and "NECROCD_ALLOWED_ROOTS" in cfg["env"]


def _stage(tmp_path, content):
    _git(tmp_path, "init", "-b", "main")
    (tmp_path / "x.py").write_text(content)
    _git(tmp_path, "add", "x.py")


def test_precommit_strict_blocks_high_only(tmp_path):
    hook = str(ROOT / ".kiro/hooks/pre-commit-exorcism.py")
    import os
    _stage(tmp_path, "def f(:\n")  # syntax rot: high severity
    env = {**os.environ, "NECROCD_STRICT": "1"}
    assert subprocess.run([sys.executable, hook], cwd=tmp_path, env=env, capture_output=True).returncode == 1
    env0 = {k: v for k, v in env.items() if k != "NECROCD_STRICT"}
    assert subprocess.run([sys.executable, hook], cwd=tmp_path, env=env0, capture_output=True).returncode == 0
    (tmp_path / "x.py").write_text("import urllib2\n")  # medium only
    _git(tmp_path, "add", "x.py")
    assert subprocess.run([sys.executable, hook], cwd=tmp_path, env=env, capture_output=True).returncode == 0


def test_install_hooks_idempotent(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    script = ROOT / "scripts/install-hooks.sh"
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
    for _ in range(2):
        subprocess.run(["bash", str(script)], cwd=tmp_path, check=True, capture_output=True)
    for name, target in [("pre-commit", "pre-commit-exorcism.py"), ("post-merge", "post-merge-exorcism.py")]:
        hook = tmp_path / ".git/hooks" / name
        assert hook.stat().st_mode & 0o100
        assert target in hook.read_text()


def test_schema_and_render_config():
    sql = (ROOT / "supabase/migrations/0001_necrocd_schema.sql").read_text()
    for t in ["ghost_telemetry", "exorcism_logs", "resurrection_metrics", "audit_trails"]:
        assert f"create table if not exists public.{t}" in sql
        assert f"alter table public.{t} enable row level security" in sql
        assert f"to authenticated using (true)" in sql
    assert sql.count("references public.") == 3 and "supabase_realtime" in sql
    render = (ROOT / "render.yaml").read_text()
    assert render.count("healthCheckPath") == 2 and "necrocd-backend" in render and "necrocd-frontend" in render
