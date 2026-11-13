import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from events import broadcaster
from ingest.engine import IngestError, clone_repo, list_graves
from models import Grave

router = APIRouter(prefix="/api", tags=["graves"])


def default_repo() -> Path:
    return Path(os.environ.get("NECROCD_REPO", Path(__file__).resolve().parents[2]))


@router.get("/graves", response_model=list[Grave])
async def graves(repo: str | None = None, url: str | None = None):
    """List graves for the local repo (NECROCD_REPO) or a GitHub URL."""
    try:
        if url:
            path = await clone_repo(url)
        elif repo:
            raise HTTPException(400, "Arbitrary local paths are not accepted; set NECROCD_REPO")
        else:
            path = default_repo()
        result = await list_graves(path)
    except IngestError as exc:
        raise HTTPException(400, str(exc))
    for g in result:
        await broadcaster.emit("grave.discovered", {"branch": g.branch, "status": g.status,
                                                    "staleness_days": g.staleness_days})
    return result
