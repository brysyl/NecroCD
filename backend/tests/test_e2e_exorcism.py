"""End to end: async clone -> libcst parse -> refactor loop -> mocked sandbox -> Supabase logging.

Uses a local temp git repo, a mocked Docker client and a fake in-memory Supabase client
(no real database was involved). The fake enforces the migration's columns and foreign keys.
"""
import re
import subprocess
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import libcst as cst
import pytest

import ingest.engine as engine
from db.supabase_client import SupabaseStore, get_store, set_store
from events import Broadcaster
from refactor.loop import exorcise
from sandbox.docker_runner import DockerRunner

LEGACY = "import urllib2\n\ndef f(n):\n    for i in xrange(n):\n        eval('1')\n"
MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "0001_necrocd_schema.sql"


def _schema():
    sql = MIGRATION.read_text()
    tables = {}
    for name, body in re.findall(r"create table if not exists public\.(\w+) \((.*?)\n\);", sql, re.S):
        cols = {}
        for line in body.splitlines():
            m = re.match(r"\s+(\w+) (\w+)", line)
            if m and m.group(1) not in ("primary", "check"):
                fk = re.search(r"references public\.(\w+)", line)
                cols[m.group(1)] = fk.group(1) if fk else None
        tables[name] = cols
    return tables


class FakeSupabase:
    def __init__(self):
        self.schema = _schema()
        self.tables = {t: [] for t in self.schema}
        self.fail = False

    def table(self, name):
        return _Query(self, name)


class _Query:
    def __init__(self, db, name):
        self.db, self.name, self.row = db, name, None

    def insert(self, row):
        self.row = dict(row)
        return self

    def execute(self):
        if self.db.fail:
            raise RuntimeError("db down")
        cols = self.db.schema[self.name]
        unknown = set(self.row) - set(cols)
        assert not unknown, f"{self.name}: columns not in migration: {unknown}"
        for col, ref in cols.items():
            if ref and self.row.get(col) is not None:
                assert any(r["id"] == self.row[col] for r in self.db.tables[ref]), f"bad FK {col}"
        self.row["id"] = str(uuid.uuid4())
        self.db.tables[self.name].append(self.row)
        return MagicMock(data=[self.row])


def _docker(exit_code=0, logs=b""):
    client = MagicMock()
    client.containers.run.return_value.wait.return_value = {"StatusCode": exit_code}
    client.containers.run.return_value.logs.return_value = logs
    return client


@pytest.fixture
def origin(tmp_path):
    repo = tmp_path / "origin"
    repo.mkdir()
    (repo / "legacy.py").write_text(LEGACY)
    run = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                    cwd=repo, check=True, capture_output=True)
    run("init", "-q")
    run("add", ".")
    run("commit", "-qm", "init")
    return repo


async def test_full_cycle_persists_everything(origin, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "validate_repo_url", lambda u: u)  # allow local path instead of github
    dest = await engine.clone_repo(str(origin), dest=tmp_path / "clone")
    source = (dest / "legacy.py").read_text()
    cst.parse_module(source)  # libcst parses the cloned file

    db = FakeSupabase()
    store = SupabaseStore(db)
    bus = Broadcaster()
    res = await exorcise(source, "legacy.py", bus, DockerRunner(lambda: _docker(0)), store=store, repo="o/r")

    assert res.ok and "range(n)" in res.new_source
    assert [e.type for e in bus.history][0] == "exorcism.started"
    tel, ex = db.tables["ghost_telemetry"], db.tables["exorcism_logs"]
    assert tel[0]["event_type"] == "exorcism.completed"
    assert ex[0]["telemetry_id"] == tel[0]["id"] and ex[0]["ok"] and ex[0]["repo"] == "o/r"
    assert len(ex[0]["findings"]) >= 2
    met = db.tables["resurrection_metrics"][0]
    assert met["exorcism_log_id"] == ex[0]["id"] and met["files_refactored"] == 1 and met["status"] == "open"
    aud = db.tables["audit_trails"][0]
    assert aud["exorcism_log_id"] == ex[0]["id"] and aud["action"] == "exorcism.ok"


async def test_sandbox_failure_logs_poltergeist(origin):
    db = FakeSupabase()
    bus = Broadcaster()
    res = await exorcise(LEGACY, "legacy.py", bus, DockerRunner(lambda: _docker(1, b"SyntaxError: bad")),
                         max_attempts=2, store=SupabaseStore(db))
    assert not res.ok
    types = [r["event_type"] for r in db.tables["ghost_telemetry"]]
    assert types.count("poltergeist") == 2 and types[-1] == "exorcism.completed"
    assert db.tables["exorcism_logs"][0]["ok"] is False and db.tables["exorcism_logs"][0]["latin_trace"]
    assert not db.tables["resurrection_metrics"]
    assert db.tables["audit_trails"][0]["action"] == "exorcism.failed"


async def test_db_failure_never_crashes_loop():
    db = FakeSupabase()
    db.fail = True
    res = await exorcise(LEGACY, "legacy.py", Broadcaster(), DockerRunner(lambda: _docker(0)),
                         store=SupabaseStore(db))
    assert res.ok


async def test_disabled_store_is_noop(monkeypatch, caplog):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    set_store(None)
    try:
        with caplog.at_level("WARNING"):
            store = get_store()
        assert not store.enabled and "persistence disabled" in caplog.text
        assert await store.log_telemetry("x") is None
        res = await exorcise(LEGACY, "legacy.py", Broadcaster(), DockerRunner(lambda: _docker(0)))
        assert res.ok
    finally:
        set_store(None)
