"""
backend/task_service.py
Unified task data layer that routes to Notion or local DB.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from backend.local_db import LocalDBClient
from backend.notion_client import NotionClient

Logger = Callable[[str, str, str, Optional[Dict[str, Any]]], None]


def _noop_logger(level: str, source: str, msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    _ = (level, source, msg, data)


class TaskService:
    def __init__(
        self,
        data_source: str,
        notion: Optional[NotionClient],
        local: Optional[LocalDBClient],
        logger: Optional[Logger] = None,
    ) -> None:
        self.data_source = (data_source or "local").lower()
        self.notion = notion
        self.local = local
        self._log: Logger = logger or _noop_logger
        self.last_fallback: Optional[str] = None

    # ── Source helpers ─────────────────────────────────────────────────────

    def _notion_ready(self) -> bool:
        return bool(self.notion and self.notion.enabled and self.notion.schema_ok)

    def effective_source(self) -> str:
        if self.data_source == "notion" and self._notion_ready():
            return "notion"
        return "local"

    def _fallback(self, op: str, reason: str) -> None:
        self.last_fallback = f"{op}: {reason}"
        self._log("WARN", "TaskService", f"{op} fell back to local", {"reason": reason})

    # ── Schema ─────────────────────────────────────────────────────────────

    def schema_summary(self) -> Dict[str, str]:
        if self.data_source == "notion" and self._notion_ready():
            return self.notion.schema_summary() if hasattr(self.notion, "schema_summary") else {}
        return self.local.schema_summary() if self.local else {}

    # ── CRUD ───────────────────────────────────────────────────────────────

    def create_task(self, task: Any) -> Optional[str]:
        if self.data_source == "notion":
            if self._notion_ready():
                pid = self.notion.create_task(task)
                if pid:
                    return pid
                self._fallback("create_task", "Notion create failed")
            else:
                self._fallback("create_task", "Notion not ready")
        return self.local.create_task(task) if self.local else None

    def update_task_status(self, task_id: str, status: str) -> bool:
        if self.data_source == "notion":
            if self._notion_ready():
                ok = self.notion.update_task_status(task_id, status)
                if ok:
                    return True
                self._fallback("update_task_status", "Notion update failed")
            else:
                self._fallback("update_task_status", "Notion not ready")
        return self.local.update_task_status(task_id, status) if self.local else False

    def update_task_properties(self, task_id: str, props: Dict[str, Any]) -> bool:
        if self.data_source == "notion":
            if self._notion_ready():
                ok = self.notion.update_task_properties(task_id, props)
                if ok:
                    return True
                self._fallback("update_task_properties", "Notion update failed")
            else:
                self._fallback("update_task_properties", "Notion not ready")
        return self.local.update_task_properties(task_id, props) if self.local else False

    def delete_task(self, task_id: str) -> bool:
        if self.data_source == "notion":
            if self._notion_ready():
                ok = self.notion.delete_task(task_id)
                if ok:
                    return True
                self._fallback("delete_task", "Notion delete failed")
            else:
                self._fallback("delete_task", "Notion not ready")
        return self.local.delete_task(task_id) if self.local else False

    def reorder_tasks(self, items: List[Dict[str, Any]]) -> int:
        if self.data_source == "notion":
            self._fallback("reorder_tasks", "Notion does not support ordering")
            return 0
        return self.local.reorder_tasks(items) if self.local else 0

    def fetch_all_tasks(self) -> List[Dict[str, Any]]:
        if self.data_source == "notion":
            if self._notion_ready():
                tasks = self.notion.fetch_all_tasks()
                if tasks is not None:
                    return tasks
                self._fallback("fetch_all_tasks", "Notion query failed")
            else:
                self._fallback("fetch_all_tasks", "Notion not ready")
        return self.local.fetch_all_tasks() if self.local else []

    def fetch_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        if self.data_source == "notion":
            if self._notion_ready():
                tasks = self.notion.fetch_tasks_by_status(status)
                if tasks is not None:
                    return tasks
                self._fallback("fetch_tasks_by_status", "Notion query failed")
            else:
                self._fallback("fetch_tasks_by_status", "Notion not ready")
        return self.local.fetch_tasks_by_status(status) if self.local else []

    def fetch_completed_topics(self) -> List[str]:
        if self.data_source == "notion" and self._notion_ready():
            return self.notion.fetch_completed_topics()
        return self.local.fetch_completed_topics() if self.local else []

    def append_study_log(self, text: str) -> None:
        if self.data_source == "notion" and self._notion_ready():
            ok = self.notion.append_study_log(text)
            if ok:
                return
            self._fallback("append_study_log", "Notion log append failed")
        if self.local:
            self.local.append_study_log(text)

    # ── Schema changes ────────────────────────────────────────────────────

    def add_column(self, *args, **kwargs) -> bool:
        if self.data_source == "notion" and self._notion_ready():
            return self.notion.add_column(*args, **kwargs)
        return self.local.add_column(*args, **kwargs) if self.local else False

    def delete_column(self, *args, **kwargs) -> bool:
        if self.data_source == "notion" and self._notion_ready():
            return self.notion.delete_column(*args, **kwargs)
        return self.local.delete_column(*args, **kwargs) if self.local else False

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "data_source": self.data_source,
            "effective_source": self.effective_source(),
            "notion_ready": self._notion_ready(),
            "local_ready": bool(self.local and self.local.enabled),
            "last_fallback": self.last_fallback,
        }
