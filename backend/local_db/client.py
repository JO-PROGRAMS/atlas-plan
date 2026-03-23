"""
backend/local_db/client.py
Local SQLite task database client (SQLAlchemy-based).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.database import SessionLocal, init_db
from backend import crud
from backend.schemas import (
    TaskCreate,
    TaskFilter,
    TaskUpdate,
    StatusEnum,
    PriorityEnum,
    EffortEnum,
)


Logger = Callable[[str, str, str, Optional[Dict[str, Any]]], None]


def _noop_logger(level: str, source: str, msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    _ = (level, source, msg, data)


class LocalDBClient:
    """
    Local task storage via SQLite + SQLAlchemy.
    Exposes a NotionClient-compatible interface used across Atlas.
    """

    def __init__(self, logger: Optional[Logger] = None) -> None:
        self._log: Logger = logger or _noop_logger
        try:
            init_db()
            self._SessionLocal = SessionLocal
            self._crud = crud
            self._TaskCreate = TaskCreate
            self._TaskUpdate = TaskUpdate
            self._StatusEnum = StatusEnum
            self._PriorityEnum = PriorityEnum
            self._EffortEnum = EffortEnum
            self.enabled = True
            self.write_enabled = True
            self.log_enabled = True
            self.list_type = "database"
            self._log("DB", "LocalDBClient", "SQLite task database ready")
        except Exception as exc:
            self._log("ERROR", "LocalDBClient", f"Init failed: {exc}")
            self.enabled = False
            self.write_enabled = False
            self.log_enabled = False
            self.list_type = "unknown"

    # ── Session context ────────────────────────────────────────────────────

    def _db(self):
        return self._SessionLocal()

    # ── Schema summary ────────────────────────────────────────────────────

    def schema_summary(self) -> Dict[str, str]:
        return {
            "Task Name": "title",
            "Status": "status",
            "Due date": "date",
            "Priority": "select",
            "Updated at": "date",
            "Effort level": "select",
            "Summary": "rich_text",
        }

    # ── Task creation ─────────────────────────────────────────────────────

    def create_task(self, task: Any) -> Optional[str]:
        if not self.write_enabled:
            self._log("WARN", "create_task", "Write disabled")
            return None
        try:
            db = self._db()
            title = self._get(task, "title", "task_name") or "Untitled"
            status = self._get(task, "status") or StatusEnum.not_started.value
            priority = self._get(task, "priority") or PriorityEnum.medium.value
            effort = self._get(task, "effort_level")
            summary = self._get(task, "summary")
            due_raw = self._get(task, "due_date") or self._get(task, "due")

            due = self._parse_due_date(due_raw)

            data = self._TaskCreate(
                task_name=str(title)[:500],
                status=self._to_enum(status, self._StatusEnum, StatusEnum.not_started),
                priority=self._to_enum(priority, self._PriorityEnum, PriorityEnum.medium),
                effort_level=self._to_enum(effort, self._EffortEnum, None) if effort else None,
                summary=str(summary)[:2000] if summary else None,
                due_date=due,
            )
            result = self._crud.create_task(db, data)
            self._log("DB", "create_task", f"Created '{title[:50]}'", {"id": result.id})
            return result.id
        except Exception as exc:
            self._log("ERROR", "create_task", f"Failed: {exc}")
            return None
        finally:
            try:
                db.close()
            except Exception:
                pass

    # ── Task updates ──────────────────────────────────────────────────────

    def update_task_status(self, task_id: str, status: str) -> bool:
        if not self.write_enabled:
            return False
        try:
            db = self._db()
            data = self._TaskUpdate(status=self._to_enum(status, self._StatusEnum, None))
            if data.status is None:
                self._log("ERROR", "update_status", f"Invalid status: {status!r}")
                return False
            t = self._crud.update_task(db, task_id, data)
            ok = t is not None
            self._log("DB", "update_status", f"{task_id[:8]} -> {status}")
            return ok
        except Exception as exc:
            self._log("ERROR", "update_status", str(exc))
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass

    def update_task_properties(self, task_id: str, props: Dict[str, Any]) -> bool:
        if not self.write_enabled:
            return False
        try:
            db = self._db()
            update_kwargs: Dict[str, Any] = {}
            if "task_name" in props or "title" in props:
                update_kwargs["task_name"] = props.get("task_name") or props.get("title")
            if "status" in props:
                update_kwargs["status"] = self._to_enum(props.get("status"), self._StatusEnum, None)
            if "priority" in props:
                update_kwargs["priority"] = self._to_enum(props.get("priority"), self._PriorityEnum, None)
            if "effort_level" in props:
                update_kwargs["effort_level"] = self._to_enum(props.get("effort_level"), self._EffortEnum, None)
            if "summary" in props:
                update_kwargs["summary"] = props.get("summary")
            if "due_date" in props or "due" in props:
                due = self._parse_due_date(props.get("due_date") or props.get("due"))
                update_kwargs["due_date"] = due

            data = self._TaskUpdate(**update_kwargs)
            t = self._crud.update_task(db, task_id, data)
            ok = t is not None
            self._log("DB", "update_props", f"{task_id[:8]}")
            return ok
        except Exception as exc:
            self._log("ERROR", "update_props", str(exc))
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass

    def update_task(self, task_id: str, props: Dict[str, Any]) -> bool:
        return self.update_task_properties(task_id, props)

    # ── Task deletion ─────────────────────────────────────────────────────

    def delete_task(self, task_id: str) -> bool:
        try:
            db = self._db()
            ok = self._crud.delete_task(db, task_id)
            self._log("DB", "delete_task", f"{task_id[:8]}")
            return ok
        except Exception as exc:
            self._log("ERROR", "delete_task", str(exc))
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass

    def archive_task(self, task_id: str) -> bool:
        try:
            db = self._db()
            t = self._crud.archive_task(db, task_id)
            ok = t is not None
            self._log("DB", "archive_task", f"{task_id[:8]}")
            return ok
        except Exception as exc:
            self._log("ERROR", "archive_task", str(exc))
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass

    # ── Reorder ───────────────────────────────────────────────────────────

    def reorder_tasks(self, items: List[Dict[str, Any]]) -> int:
        try:
            db = self._db()
            from backend.schemas import ReorderItem
            parsed = [ReorderItem(**i) for i in items]
            updated = self._crud.reorder_tasks(db, parsed)
            self._log("DB", "reorder", f"updated={updated}")
            return updated
        except Exception as exc:
            self._log("ERROR", "reorder", str(exc))
            return 0
        finally:
            try:
                db.close()
            except Exception:
                pass

    # ── Queries ───────────────────────────────────────────────────────────

    def fetch_all_tasks(self) -> List[Dict[str, Any]]:
        try:
            db = self._db()
            items, _ = self._crud.get_tasks(db, TaskFilter(page_size=200))
            return [self._task_to_dict(t) for t in items]
        except Exception as exc:
            self._log("ERROR", "fetch_all_tasks", str(exc))
            return []
        finally:
            try:
                db.close()
            except Exception:
                pass

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        return self.fetch_all_tasks()

    def fetch_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        try:
            db = self._db()
            items, _ = self._crud.get_tasks(
                db, TaskFilter(status=self._to_enum(status, self._StatusEnum, None), page_size=200)
            )
            return [self._task_to_dict(t) for t in items]
        except Exception as exc:
            self._log("ERROR", "fetch_tasks_by_status", str(exc))
            return []
        finally:
            try:
                db.close()
            except Exception:
                pass

    def fetch_completed_topics(self) -> List[str]:
        return [t["task_name"] for t in self.fetch_tasks_by_status("Done") if t.get("task_name")]

    def append_study_log(self, text: str) -> None:
        try:
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_path = os.path.join(root, "atlas_study_log.txt")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {text}\n")
        except Exception as exc:
            self._log("WARN", "append_study_log", str(exc))

    # ── Schema changes (no-op) ────────────────────────────────────────────

    def add_column(self, *args, **kwargs) -> bool:
        self._log("WARN", "add_column", "Schema changes not supported in local DB mode")
        return False

    def delete_column(self, *args, **kwargs) -> bool:
        self._log("WARN", "delete_column", "Schema changes not supported in local DB mode")
        return False

    # ── Extractors ─────────────────────────────────────────────────────────

    @staticmethod
    def get_task_title(task_dict: Dict[str, Any]) -> str:
        return task_dict.get("task_name", "") or ""

    @staticmethod
    def get_task_status(task_dict: Dict[str, Any]) -> str:
        return task_dict.get("status", StatusEnum.not_started.value) or StatusEnum.not_started.value

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _get(obj: Any, *names: str) -> Any:
        if isinstance(obj, dict):
            for n in names:
                if n in obj and obj.get(n) is not None:
                    return obj.get(n)
            return None
        for n in names:
            if hasattr(obj, n):
                v = getattr(obj, n)
                if v is not None:
                    return v
        return None

    @staticmethod
    def _to_enum(value: Any, enum_cls: Any, default: Any) -> Any:
        if value is None:
            return default
        try:
            return enum_cls(value)
        except Exception:
            return default

    @staticmethod
    def _parse_due_date(raw: Any) -> Optional[datetime]:
        if raw is None or raw == "":
            return None
        if isinstance(raw, datetime):
            return raw
        try:
            raw_str = str(raw).strip()
            if "T" in raw_str:
                if raw_str.endswith("Z"):
                    raw_str = raw_str.replace("Z", "+00:00")
                if len(raw_str.split("T")[1].split("+")[0].split("Z")[0]) == 5:
                    raw_str += ":00"
                return datetime.fromisoformat(raw_str)
            # Date-only
            return datetime.fromisoformat(f"{raw_str}T09:00:00")
        except Exception:
            return None

    @staticmethod
    def _task_to_dict(task: Any) -> Dict[str, Any]:
        return {
            "id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "priority": task.priority,
            "effort_level": task.effort_level or "",
            "summary": task.summary or "",
            "due_date": task.due_date.isoformat() if task.due_date else "",
            "due": task.due_date.isoformat() if task.due_date else "",
            "position": task.position,
            "archived": task.archived,
            "created_at": task.created_at.isoformat() if task.created_at else "",
            "updated_at": task.updated_at.isoformat() if task.updated_at else "",
        }

    @staticmethod
    def _s(v: Any) -> str:
        if isinstance(v, list):
            v = v[0] if v else ""
        return str(v).strip() if v else ""

    @staticmethod
    def _format_due_date(raw: str) -> Optional[str]:
        if not raw:
            return None
        raw = raw.strip()
        if "T" in raw:
            parts = raw.split("T")
            time_part = parts[1].split("+")[0].split("Z")[0]
            if len(time_part) == 5:
                raw = f"{parts[0]}T{time_part}:00"
            return raw
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return f"{raw}T09:00:00"
        except ValueError:
            return None
