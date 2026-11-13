"""Refactoring loop: analyze -> transform -> sandbox test -> emit events, with retries."""
from __future__ import annotations

import libcst as cst

from events import Broadcaster
from models import RefactorResult
from parser.ast_analyzer import analyze_source
from refactor.transformers import generate_component, generate_router, modernize, source_hash
from sandbox.docker_runner import DockerRunner, SandboxResult


async def exorcise(source: str, file: str, bus: Broadcaster, runner: DockerRunner | None = None,
                   max_attempts: int = 3) -> RefactorResult:
    runner = runner or DockerRunner()
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
            await bus.poltergeist("syntax rot", last_error)
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
        await bus.poltergeist("test failure" if not test.daemon_missing else "dependency error", last_error or "")
        if test.daemon_missing:
            break
        current = new_source
    result.error = last_error
    await bus.emit("exorcism.completed", {"target": file, "ok": result.ok, "attempts": result.attempts,
                                          "findings": len(findings)})
    return result
