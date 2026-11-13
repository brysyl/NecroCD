"""NecroCD pre-commit hook: analyze staged Python files with the AST analyzer.

Set NECROCD_STRICT=1 to block commits containing high severity findings.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))


def staged_python_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f.endswith(".py")]


def staged_content(path: str) -> str:
    return subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True).stdout


def scan_for_ghosts() -> int:
    from parser.ast_analyzer import analyze_source

    print("[!] NecroCD Hook: Scanning staging area for legacy cursed code...")
    findings = []
    for f in staged_python_files():
        findings.extend(analyze_source(staged_content(f), f))
    for fd in findings:
        print(f"  {fd.file}:{fd.line} [{fd.severity}] {fd.rule}: {fd.message} ({fd.symbol or '-'})")
    if findings:
        print(f"[!] POLTERGEIST WARNING: {len(findings)} haunting(s) detected. Run the exorcism pipeline.")
    if os.environ.get("NECROCD_STRICT") == "1" and any(f.severity in ("high", "critical") for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(scan_for_ghosts())
