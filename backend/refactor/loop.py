"""Refactoring loop: analyze -> transform -> sandbox test -> emit events, with retries."""
from __future__ import annotations

import logging

import libcst as cst

from db.supabase_client import SupabaseStore, get_store
from events import Broadcaster
from models import RefactorResult
from parser.ast_analyzer import analyze_source
from refactor.transformers import generate_component, generate_router, modernize, source_hash
from sandbox.docker_runner import DockerRunner, SandboxResult

log = logging.getLogger("necrocd.refactor")


async def exorcise(source: str, file: str, bus: Broadcaster, runner: DockerRunner | None = None,
                   max_attempts: int = 3, store: SupabaseStore | None = None,
                   repo: str | None = None) -> RefactorResult:
    runner = runner or DockerRunner()
    store = store or get_store()
    latin_traces: list[str] = []
    await bus.emit("exorcism.started", {"target": file})
    result = RefactorResult(file=file, ok=False, original_hash=source_hash(source))
    findings = analyze_source(source, file)
    current = source
    last_error = None
    for attempt in range(1, max_attempts + 1):
        result.attempts = attempt
        await bus.emit("exorcism.step", {"attempt": attempt, "stage": "analyze"})
        try:
            await bus.emit("exorcism.step", {"attempt": attempt, "stage": "transform"})
            new_source, applied = modernize(current)
        except cst.ParserSyntaxError as exc:
            last_error = f"SyntaxError: {exc}"
            ev = await bus.poltergeist("syntax rot", last_error)
            latin_traces.append(ev.payload["latin"])
            await store.log_telemetry("poltergeist", ev.payload, repo=repo)
            break  # retrying cannot fix unparseable source
        await bus.emit("exorcism.step", {"attempt": attempt, "stage": "test"})
        test: SandboxResult = await runner.run_python(new_source)
        if test.ok:
            result.ok = True
            result.new_source = new_source
            result.applied = applied
            result.router_source = generate_router(new_source)
            result.component_source = generate_component(new_source, file.rsplit("/", 1)[-1].split(".")[0])
            last_error = None
            break
        last_error = test.error or test.logs
        ev = await bus.poltergeist("test failure" if not test.daemon_missing else "dependency error", last_error or "")
        latin_traces.append(ev.payload["latin"])
        await store.log_telemetry("poltergeist", ev.payload, repo=repo)
        if test.daemon_missing:
            break
        current = new_source
    result.error = last_error
    done = await bus.emit("exorcism.completed", {"target": file, "ok": result.ok, "attempts": result.attempts,
                                                 "findings": len(findings)})
    await _persist(store, result, findings, done.payload, latin_traces, repo)
    return result


async def _persist(store: SupabaseStore, result: RefactorResult, findings: list, payload: dict,
                   latin_traces: list[str], repo: str | None) -> None:
    """Write telemetry, exorcism log, metrics and audit trail; never raises."""
    try:
        telemetry_id = await store.log_telemetry("exorcism.completed", payload, repo=repo)
        log_id = await store.log_exorcism(
            result.file, result.ok, result.attempts, [f.model_dump() for f in findings],
            error=result.error, latin_trace="\n".join(latin_traces) or None,
            telemetry_id=telemetry_id, repo=repo)
        if result.ok:
            await store.log_resurrection(repo or result.file, 1, len(result.applied), exorcism_log_id=log_id)
        await store.log_audit("necrocd", "exorcism.ok" if result.ok else "exorcism.failed", result.file,
                              exorcism_log_id=log_id, details={"attempts": result.attempts})
    except Exception:  # persistence must never break the loop
        log.exception("persisting exorcism result failed")
