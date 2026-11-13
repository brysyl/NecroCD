"""Pydantic v2 contracts (see .kiro/specs/02-ast-transformation-schema.md)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high", "critical"]


class Finding(BaseModel):
    rule: str
    severity: Severity = "medium"
    file: str
    line: int = 0
    message: str
    symbol: Optional[str] = None
    suggestion: Optional[str] = None


class TransformStep(BaseModel):
    kind: Literal["replace-import", "replace-call", "generate-router", "generate-component"]
    target: str
    replacement: Optional[str] = None


class TransformPlan(BaseModel):
    file: str
    steps: list[TransformStep] = Field(default_factory=list)


class RefactorResult(BaseModel):
    file: str
    ok: bool
    original_hash: str = ""
    new_source: Optional[str] = None
    applied: list[TransformStep] = Field(default_factory=list)
    router_source: Optional[str] = None
    component_source: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None


class Grave(BaseModel):
    branch: str
    last_commit: str
    last_commit_date: str
    staleness_days: int
    status: Literal["broken", "restable"]
    findings: int = 0


class TelemetryEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: str
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
