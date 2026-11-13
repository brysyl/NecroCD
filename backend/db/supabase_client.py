"""Supabase persistence for ghost telemetry, exorcism logs, resurrection metrics and audit trails.

Column names match supabase/migrations/0001_necrocd_schema.sql. When SUPABASE_URL or
SUPABASE_SERVICE_KEY is unset the store is a no-op (one logged warning). Every write is
wrapped so a database failure is logged and never propagates into the exorcism loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

log = logging.getLogger("necrocd.db")


class SupabaseStore:
    def __init__(self, client: Any = None) -> None:
        self.client = client

    @property
    def enabled(self) -> bool:
        return self.client is not None

    @classmethod
    def from_env(cls) -> "SupabaseStore":
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        if not url or not key:
            log.warning("SUPABASE_URL/SUPABASE_SERVICE_KEY not set: persistence disabled (no-op)")
            return cls(None)
        try:
            from supabase import create_client

            return cls(create_client(url, key))
        except Exception as exc:
            log.warning("Supabase client init failed, persistence disabled: %s", exc)
            return cls(None)

    def _insert_sync(self, table: str, row: dict) -> Optional[str]:
        res = self.client.table(table).insert(row).execute()
        data = getattr(res, "data", None) or []
        return data[0].get("id") if data else None

    async def _insert(self, table: str, row: dict) -> Optional[str]:
        """Insert a row and return its id; returns None when disabled or on any failure."""
        if not self.enabled:
            return None
        try:
            return await asyncio.to_thread(self._insert_sync, table, row)
        except Exception as exc:
            log.warning("Supabase insert into %s failed: %s", table, exc)
            return None

    async def log_telemetry(self, event_type: str, payload: Optional[dict] = None,
                            repo: Optional[str] = None, branch: Optional[str] = None) -> Optional[str]:
        return await self._insert("ghost_telemetry", {
            "event_type": event_type, "repo": repo, "branch": branch, "payload": payload or {}})

    async def log_exorcism(self, file: str, ok: bool, attempts: int, findings: list[dict],
                           error: Optional[str] = None, latin_trace: Optional[str] = None,
                           telemetry_id: Optional[str] = None, repo: Optional[str] = None) -> Optional[str]:
        return await self._insert("exorcism_logs", {
            "telemetry_id": telemetry_id, "repo": repo, "file": file, "ok": ok,
            "attempts": max(attempts, 0), "findings": findings, "error": error, "latin_trace": latin_trace})

    async def log_resurrection(self, repo: str, files_refactored: int, findings_fixed: int,
                               exorcism_log_id: Optional[str] = None, pr_number: Optional[int] = None,
                               pr_url: Optional[str] = None, status: str = "open") -> Optional[str]:
        return await self._insert("resurrection_metrics", {
            "repo": repo, "pr_number": pr_number, "pr_url": pr_url, "status": status,
            "files_refactored": files_refactored, "findings_fixed": findings_fixed,
            "exorcism_log_id": exorcism_log_id})

    async def log_audit(self, actor: str, action: str, target: Optional[str] = None,
                        exorcism_log_id: Optional[str] = None, details: Optional[dict] = None) -> Optional[str]:
        return await self._insert("audit_trails", {
            "actor": actor, "action": action, "target": target,
            "exorcism_log_id": exorcism_log_id, "details": details or {}})


_store: Optional[SupabaseStore] = None


def get_store() -> SupabaseStore:
    global _store
    if _store is None:
        _store = SupabaseStore.from_env()
    return _store


def set_store(store: Optional[SupabaseStore]) -> None:
    """Override (or reset with None) the process-wide store; used by tests."""
    global _store
    _store = store
