"""Async ingestion engine: clone repos or read local git history."""
from __future__ import annotations

import asyncio
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from models import Grave
from parser.ast_analyzer import analyze_tree

GITHUB_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?(\.git)?/?$")
STALE_DAYS = 90


class IngestError(Exception):
    pass


def validate_repo_url(url: str) -> str:
    if not GITHUB_URL.match(url):
        raise IngestError("Only https://github.com/<owner>/<repo> URLs are allowed")
    return url


async def _git(*args: str, cwd: Path | None = None, timeout: float = 120) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise IngestError(f"git {args[0]} timed out")
    if proc.returncode != 0:
        raise IngestError(f"git {args[0]} failed: {err.decode(errors='replace').strip()}")
    return out.decode(errors="replace")


async def clone_repo(url: str, depth: int = 50, dest: Path | None = None) -> Path:
    validate_repo_url(url)
    dest = dest or Path(tempfile.mkdtemp(prefix="necrocd-"))
    await _git("clone", f"--depth={int(depth)}", "--no-single-branch", "--", url, str(dest))
    return dest


async def list_graves(repo: Path, stale_days: int = STALE_DAYS, scan: bool = True) -> list[Grave]:
    """Return one grave per branch with staleness and broken/restable status."""
    if not (Path(repo) / ".git").exists():
        raise IngestError(f"Not a git repository: {repo}")
    fmt = "%(refname:short)|%(objectname:short)|%(committerdate:iso-strict)"
    out = await _git("for-each-ref", f"--format={fmt}", "refs/heads", "refs/remotes", cwd=repo)
    now = datetime.now(timezone.utc)
    graves: list[Grave] = []
    for line in out.splitlines():
        name, sha, date = line.split("|", 2)
        if name.endswith("/HEAD") or name == "origin":
            continue
        age = max((now - datetime.fromisoformat(date)).days, 0)
        graves.append(Grave(branch=name, last_commit=sha, last_commit_date=date,
                            staleness_days=age, status="restable"))
    if scan and graves:
        findings = analyze_tree(Path(repo))  # working tree = checked out branch
        current = (await _git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo)).strip()
        bad = sum(1 for f in findings if f.severity in ("high", "critical"))
        for g in graves:
            if g.branch == current:
                g.findings = len(findings)
                g.status = "broken" if bad else "restable"
    return sorted(graves, key=lambda g: -g.staleness_days)


def stale_only(graves: list[Grave], stale_days: int = STALE_DAYS) -> list[Grave]:
    return [g for g in graves if g.staleness_days >= stale_days]
