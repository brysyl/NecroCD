from fastapi import APIRouter
from pydantic import BaseModel, Field

from events import broadcaster
from models import RefactorResult
from refactor.loop import exorcise
from sandbox.docker_runner import DockerRunner

router = APIRouter(prefix="/api", tags=["exorcism"])
runner = DockerRunner()


class ExorcismRequest(BaseModel):
    file: str = "module.py"
    source: str = Field(max_length=200_000)
    max_attempts: int = Field(default=3, ge=1, le=5)


@router.post("/exorcism", response_model=RefactorResult)
async def run_exorcism(req: ExorcismRequest):
    return await exorcise(req.source, req.file, broadcaster, runner, req.max_attempts)
