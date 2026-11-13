"""Secure Docker sandbox runner."""
from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

IMAGE = "python:3.11-slim"


@dataclass
class SandboxResult:
    ok: bool
    exit_code: int = -1
    logs: str = ""
    error: str | None = None
    daemon_missing: bool = False


def _client() -> Any:
    import docker  # lazy: keeps import light and mockable

    return docker.from_env()


class DockerRunner:
    def __init__(self, client_factory=_client, image: str = IMAGE, timeout: int = 30,
                 mem_limit: str = "128m", nano_cpus: int = 500_000_000, pids_limit: int = 64) -> None:
        self.client_factory = client_factory
        self.image = image
        self.timeout = timeout
        self.mem_limit = mem_limit
        self.nano_cpus = nano_cpus
        self.pids_limit = pids_limit

    def _run_sync(self, source: str) -> SandboxResult:
        try:
            client = self.client_factory()
            client.ping()
        except Exception as exc:
            return SandboxResult(False, error=f"Docker daemon unavailable: {exc}", daemon_missing=True)
        container = None
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "main.py").write_text(source, encoding="utf-8")
            try:
                container = client.containers.run(
                    self.image,
                    ["python", "-I", "-m", "py_compile", "/work/main.py"],
                    detach=True,
                    network_disabled=True,
                    network_mode="none",
                    mem_limit=self.mem_limit,
                    nano_cpus=self.nano_cpus,
                    pids_limit=self.pids_limit,
                    read_only=True,
                    cap_drop=["ALL"],
                    security_opt=["no-new-privileges"],
                    user="nobody",
                    volumes={tmp: {"bind": "/work", "mode": "ro"}},
                    environment={"PYTHONDONTWRITEBYTECODE": "1"},
                )
                try:
                    res = container.wait(timeout=self.timeout)
                    code = int(res.get("StatusCode", -1))
                except Exception as exc:
                    container.kill()
                    return SandboxResult(False, error=f"Sandbox timed out: {exc}")
                logs = container.logs().decode("utf-8", "replace")
                return SandboxResult(code == 0, code, logs, None if code == 0 else logs)
            except Exception as exc:
                return SandboxResult(False, error=f"Sandbox failure: {exc}")
            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

    async def run_python(self, source: str) -> SandboxResult:
        return await asyncio.to_thread(self._run_sync, source)
