import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from events import Broadcaster
from ingest.engine import IngestError, list_graves, validate_repo_url
from main import app
from parser.ast_analyzer import analyze_source
from poltergeist import translate_trace
from refactor.loop import exorcise
from refactor.transformers import generate_component, generate_router, modernize
from sandbox.docker_runner import DockerRunner

LEGACY = "import urllib2\nimport Queue\n\ndef fetch(url, n):\n    for i in xrange(n):\n        eval(url)\n    return Queue.Queue()\n"


def test_analyzer_findings():
    rules = {(f.rule, f.symbol) for f in analyze_source(LEGACY, "a.py")}
    assert ("legacy-import", "urllib2") in rules
    assert ("deprecated-call", "xrange") in rules
    assert ("security-risk", "eval") in rules


def test_analyzer_syntax_rot():
    f = analyze_source('print "hi"\n', "p.py")
    assert f and f[0].rule == "syntax-rot" and f[0].line == 1
    assert analyze_source("def (:\n")[0].rule == "syntax-rot"


def test_transformer_idempotent_and_formatting():
    new, applied = modernize(LEGACY)
    assert "import queue as Queue" in new and "range(n)" in new
    assert len(applied) == 2
    again, applied2 = modernize(new)
    assert again == new and applied2 == []


def test_generators():
    r = generate_router(LEGACY)
    compile(r, "r", "exec")
    assert "/fetch" in r
    assert "export default function" in generate_component(LEGACY, "legacy")


def test_translate():
    assert "Modulus perditus" in translate_trace("ModuleNotFoundError: x")


def test_url_validation():
    validate_repo_url("https://github.com/a/b")
    for bad in ["file:///etc", "https://evil.com/a/b", "https://github.com/a/b; rm -rf /"]:
        with pytest.raises(IngestError):
            validate_repo_url(bad)


async def test_list_graves(tmp_path):
    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    g("init", "-b", "main")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (tmp_path / "a.py").write_text('print "x"\n')
    g("add", ".")
    g("commit", "-m", "old")
    g("branch", "dead")
    graves = await list_graves(tmp_path)
    assert {x.branch for x in graves} == {"main", "dead"}
    assert next(x for x in graves if x.branch == "main").status == "broken"
    with pytest.raises(IngestError):
        await list_graves(tmp_path / "nope")


def _mock_client(code=0):
    client = MagicMock()
    c = client.containers.run.return_value
    c.wait.return_value = {"StatusCode": code}
    c.logs.return_value = b"boom"
    return client, c


async def test_sandbox_flags():
    client, c = _mock_client()
    r = await DockerRunner(lambda: client).run_python("x=1")
    assert r.ok
    kw = client.containers.run.call_args.kwargs
    assert kw["network_mode"] == "none" and kw["read_only"] and kw["cap_drop"] == ["ALL"]
    assert kw["pids_limit"] and kw["mem_limit"]
    c.remove.assert_called_once_with(force=True)


async def test_sandbox_failure_and_missing_daemon():
    client, _ = _mock_client(1)
    assert not (await DockerRunner(lambda: client).run_python("x")).ok

    def boom():
        raise RuntimeError("no daemon")
    r = await DockerRunner(boom).run_python("x")
    assert r.daemon_missing and not r.ok


async def test_exorcise_loop_events():
    bus = Broadcaster()
    client, _ = _mock_client()
    res = await exorcise(LEGACY, "legacy/mod.py", bus, DockerRunner(lambda: client))
    assert res.ok and "queue" in res.new_source
    types = [e.type for e in bus.history]
    assert types[0] == "exorcism.started" and types[-1] == "exorcism.completed"

    bus2 = Broadcaster()
    client2, _ = _mock_client(1)
    res2 = await exorcise(LEGACY, "m.py", bus2, DockerRunner(lambda: client2), max_attempts=2)
    assert not res2.ok and res2.attempts == 2
    assert any(e.type == "poltergeist" for e in bus2.history)


def test_api_and_ws():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "alive"
        r = c.get("/api/graves")
        assert r.status_code == 200 and isinstance(r.json(), list)
        assert c.get("/api/graves", params={"repo": "/etc"}).status_code == 400
        with c.websocket_connect("/ws/telemetry") as ws:
            assert ws.receive_json()["type"] == "hello"
            c.post("/api/telemetry/poltergeist", json={"trace": "AssertionError"})
            ev = ws.receive_json()
            assert ev["type"] == "poltergeist" and "Probatio" in ev["payload"]["latin"]
