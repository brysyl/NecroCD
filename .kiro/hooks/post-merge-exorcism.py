"""NecroCD post-merge hook: report stale/dead branches after a merge."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from ingest.engine import IngestError, list_graves, stale_only

    try:
        graves = asyncio.run(list_graves(ROOT))
    except IngestError as exc:
        print(f"[!] NecroCD post-merge: {exc}")
        return 0
    dead = stale_only(graves)
    print(f"[!] NecroCD post-merge: {len(dead)} dead branch(es) in the graveyard.")
    for g in dead:
        print(f"  {g.branch}: {g.staleness_days}d stale ({g.status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
