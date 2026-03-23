"""
backend/notion_client.py
Notion API client for Atlas task database.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

Logger = Callable[[str, str, str, Optional[Dict[str, Any]]], None]


def _noop_logger(level: str, source: str, msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    _ = (level, source, msg, data)


STATUS_NOT_STARTED = "Not started"
STATUS_IN_PROGRESS = "In progress"
STATUS_DONE = "Done"
STATUS_PLANNED = "Planned"

VALID_STATUSES = {STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_PLANNED}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_EFFORTS = {"Small", "Medium", "Large"}

REQUIRED_PROPERTIES: Dict[str, str] = {
    "Task Name": "title",
    "Status": "status",
    "Due date": "date",
    "Priority": "select",
    "Updated at": "date",
    "Effort level": "select",
    "Summary": "rich_text",
}

# Alternate label candidates (case/spacing variations) mapped to logical keys
PROPERTY_CANDIDATES: Dict[str, List[str]] = {
    "Task Name": ["Task Name", "Task name", "Name", "Title"],
    "Status": ["Status"],
    "Due date": ["Due date", "Due Date", "Due"],
    "Priority": ["Priority"],
    "Updated at": ["Updated at", "Last updated", "Last Edited"],
    "Effort level": ["Effort level", "Effort Level", "Effort"],
    "Summary": ["Summary", "Notes", "Description"],
}


class NotionClient:
    """Notion client with schema validation and strict payload checks."""

    def __init__(
        self,
        token: str,
        database_id: str,
        study_log_page_id: str = "",
        api_version: str = "2025-09-03",
        logger: Optional[Logger] = None,
    ) -> None:
        self.token = (token or "").strip()
        self.database_id = (database_id or "").strip()
        self.study_log_page_id = (study_log_page_id or "").strip()
        self._api_version = api_version
        self._log: Logger = logger or _noop_logger

        self.base_url = "https://api.notion.com/v1"
        self.enabled = bool(self.token and self.database_id)
        self.write_enabled = self.enabled
        self.log_enabled = bool(self.study_log_page_id)
        self.list_type = "unknown"

        self.data_source_id: Optional[str] = None
        self.db_properties: Dict[str, Any] = {}
        self.schema_ok = False
        self.allowed_statuses: List[str] = []
        self.allowed_priorities: List[str] = []
        self.allowed_efforts: List[str] = []
        self.prop_names: Dict[str, str] = {}
        self.last_error: Optional[str] = None

        if self.enabled:
            self.refresh_schema()
        else:
            self._log("ERROR", "NotionClient", "Missing token or database_id")

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self._api_version,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 20,
    ) -> Tuple[bool, Dict[str, Any], int]:
        url = f"{self.base_url}{path}"
        try:
            r = requests.request(
                method,
                url,
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            )
        except Exception as exc:
            return False, {"error": str(exc)}, 0
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        return r.ok, data, r.status_code

    def _log_request(
        self,
        source: str,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]],
        ok: bool,
        status: int,
        response: Dict[str, Any],
    ) -> None:
        self._log(
            "NOTION" if ok else "ERROR",
            source,
            f"{method} {path} -> {status}",
            {"request": payload, "response": response},
        )

    # ── Schema ────────────────────────────────────────────────────────────

    def refresh_schema(self) -> bool:
        if not self.enabled:
            return False

        ok, db, status = self._request("GET", f"/databases/{self.database_id}")
        self._log_request("schema", "GET", f"/databases/{self.database_id}", None, ok, status, db)
        if not ok:
            self.enabled = False
            self.write_enabled = False
            self.list_type = "unknown"
            self.last_error = f"Schema fetch failed (HTTP {status})"
            return False

        # New API: database contains data_sources array
        data_sources = db.get("data_sources") or []
        if data_sources:
            self.data_source_id = data_sources[0].get("id")
            if not self.data_source_id:
                self._log("ERROR", "schema", "data_sources present but id missing", {"data_sources": data_sources})
                self.enabled = False
                self.write_enabled = False
                self.last_error = "Schema fetch failed (missing data_source_id)"
                return False
            ok2, ds, status2 = self._request("GET", f"/data_sources/{self.data_source_id}")
            self._log_request(
                "schema",
                "GET",
                f"/data_sources/{self.data_source_id}",
                None,
                ok2,
                status2,
                ds,
            )
            if not ok2:
                self.enabled = False
                self.write_enabled = False
                self.last_error = f"Data source fetch failed (HTTP {status2})"
                return False
            self.db_properties = ds.get("properties", {}) or {}
        else:
            self.db_properties = db.get("properties", {}) or {}

        return self._validate_schema()

    def _validate_schema(self) -> bool:
        errors: List[str] = []
        props = self.db_properties or {}
        self.prop_names = self._resolve_property_names(props)
        for logical, expected_type in REQUIRED_PROPERTIES.items():
            actual = self.prop_names.get(logical)
            if not actual:
                errors.append(f"Missing property '{logical}'")
                continue
            prop = props.get(actual) or {}
            if prop.get("type") != expected_type:
                errors.append(
                    f"Property '{actual}' type mismatch (expected {expected_type}, got {prop.get('type')})"
                )
            # Enforce exact name match (case-sensitive)
            if actual != logical:
                errors.append(
                    f"Property name mismatch: expected '{logical}', found '{actual}'. Rename in Notion to match."
                )

        # Validate options for status/select types
        self.allowed_statuses = self._extract_options(props, self.prop_names.get("Status", "Status"), "status")
        self.allowed_priorities = self._extract_options(props, self.prop_names.get("Priority", "Priority"), "select")
        self.allowed_efforts = self._extract_options(props, self.prop_names.get("Effort level", "Effort level"), "select")

        if self.prop_names.get("Status") and not self.allowed_statuses:
            errors.append("Status options could not be read from schema")
        if self.prop_names.get("Priority") and not self.allowed_priorities:
            errors.append("Priority options could not be read from schema")
        if self.prop_names.get("Effort level") and not self.allowed_efforts:
            errors.append("Effort level options could not be read from schema")

        if self.allowed_statuses and not VALID_STATUSES.issubset(set(self.allowed_statuses)):
            errors.append(f"Status options missing required values: {sorted(VALID_STATUSES)}")
        if self.allowed_priorities and not VALID_PRIORITIES.issubset(set(self.allowed_priorities)):
            errors.append(f"Priority options missing required values: {sorted(VALID_PRIORITIES)}")
        if self.allowed_efforts and not VALID_EFFORTS.issubset(set(self.allowed_efforts)):
            errors.append(f"Effort options missing required values: {sorted(VALID_EFFORTS)}")

        if errors:
            self._log("ERROR", "schema", "Schema validation failed", {"errors": errors})
            self.schema_ok = False
            self.list_type = "unknown"
            self.write_enabled = False
            self.last_error = "Schema validation failed: " + "; ".join(errors[:5])
            return False

        self.schema_ok = True
        self.list_type = "database"
        return True

    def schema_summary(self) -> Dict[str, str]:
        if not self.prop_names:
            return dict(REQUIRED_PROPERTIES)
        return {
            self.prop_names.get(k, k): v for k, v in REQUIRED_PROPERTIES.items()
        }

    @staticmethod
    def _extract_options(props: Dict[str, Any], name: str, prop_type: str) -> List[str]:
        prop = props.get(name) or {}
        if prop.get("type") != prop_type:
            return []
        cfg = prop.get(prop_type) or {}
        opts = cfg.get("options") or []
        return [o.get("name") for o in opts if o.get("name")]

    @staticmethod
    def _resolve_property_names(props: Dict[str, Any]) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        keys = list(props.keys())
        lower_map = {k.lower(): k for k in keys}
        for logical, candidates in PROPERTY_CANDIDATES.items():
            found = None
            for cand in candidates:
                if cand in props:
                    found = cand
                    break
                lc = cand.lower()
                if lc in lower_map:
                    found = lower_map[lc]
                    break
            if found:
                resolved[logical] = found
        return resolved

    # ── Payload helpers ───────────────────────────────────────────────────

    @staticmethod
    def _plain_text(items: List[Dict[str, Any]]) -> str:
        return "".join([i.get("plain_text", "") for i in items if i])

    @staticmethod
    def _normalize_date(raw: str) -> Optional[str]:
        if not raw:
            return None
        raw = str(raw).strip()
        if "T" in raw:
            if raw.endswith("Z"):
                return raw
            if len(raw.split("T")[1].split("+")[0].split("Z")[0]) == 5:
                raw += ":00"
            return raw
        # Date-only -> set a default time
        return f"{raw}T09:00:00Z"

    def _now_iso(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _validate_task_fields(self, title: str, status: Optional[str], priority: Optional[str],
                              effort: Optional[str], due_date: Optional[str]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not title:
            errors.append("Title is required")
        if status and self.allowed_statuses and status not in self.allowed_statuses:
            errors.append(f"Invalid status: {status}")
        if priority and self.allowed_priorities and priority not in self.allowed_priorities:
            errors.append(f"Invalid priority: {priority}")
        if effort and self.allowed_efforts and effort not in self.allowed_efforts:
            errors.append(f"Invalid effort level: {effort}")
        if due_date and not self._normalize_date(due_date):
            errors.append(f"Invalid due_date: {due_date}")
        return (len(errors) == 0, errors)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create_task(self, task: Any) -> Optional[str]:
        if not (self.enabled and self.schema_ok and self.write_enabled):
            self._log("ERROR", "create_task", "Notion not ready")
            return None

        title = self._get(task, "title", "task_name") or "Untitled"
        status = self._get(task, "status") or STATUS_NOT_STARTED
        priority = self._get(task, "priority") or "Medium"
        effort = self._get(task, "effort_level")
        summary = self._get(task, "summary") or ""
        due_raw = self._get(task, "due_date") or self._get(task, "due")
        due = self._normalize_date(due_raw) if due_raw else None

        ok, errs = self._validate_task_fields(title, status, priority, effort, due)
        if not ok:
            self._log("ERROR", "create_task", "Validation failed", {"errors": errs})
            return None

        tn = self.prop_names.get("Task Name", "Task Name")
        st = self.prop_names.get("Status", "Status")
        pr = self.prop_names.get("Priority", "Priority")
        du = self.prop_names.get("Due date", "Due date")
        up = self.prop_names.get("Updated at", "Updated at")
        ef = self.prop_names.get("Effort level", "Effort level")
        sm = self.prop_names.get("Summary", "Summary")

        props: Dict[str, Any] = {
            tn: {"title": [{"text": {"content": str(title)}}]},
            st: {"status": {"name": status}},
            pr: {"select": {"name": priority}},
            up: {"date": {"start": self._now_iso()}},
        }
        if due:
            props[du] = {"date": {"start": due}}
        if effort:
            props[ef] = {"select": {"name": effort}}
        if summary:
            props[sm] = {"rich_text": [{"text": {"content": str(summary)}}]}
        else:
            props[sm] = {"rich_text": []}

        parent: Dict[str, Any]
        if self.data_source_id:
            parent = {"type": "data_source_id", "data_source_id": self.data_source_id}
        else:
            parent = {"type": "database_id", "database_id": self.database_id}

        payload = {"parent": parent, "properties": props}
        ok, resp, status_code = self._request("POST", "/pages", payload)
        self._log_request("create_task", "POST", "/pages", payload, ok, status_code, resp)
        if not ok:
            self.last_error = f"Create failed (HTTP {status_code})"
            return None
        page_id = resp.get("id")
        if not page_id:
            self.last_error = "Create succeeded but no page id returned"
            return None

        # Re-fetch created page to confirm persistence
        ok2, page, status2 = self._request("GET", f"/pages/{page_id}")
        self._log_request("create_task_confirm", "GET", f"/pages/{page_id}", None, ok2, status2, page)
        if not ok2:
            self.last_error = f"Create confirmation failed (HTTP {status2})"
            return None

        # Confirm parent matches database/data source
        parent = (page or {}).get("parent") or {}
        if self.data_source_id:
            if parent.get("data_source_id") != self.data_source_id:
                self._log("ERROR", "create_task_confirm", "Parent data_source_id mismatch", {"parent": parent})
                self.last_error = "Parent data_source_id mismatch"
                return None
        else:
            if parent.get("database_id") != self.database_id:
                self._log("ERROR", "create_task_confirm", "Parent database_id mismatch", {"parent": parent})
                self.last_error = "Parent database_id mismatch"
                return None

        return page_id

    def update_task_status(self, task_id: str, status: str) -> bool:
        if not (self.enabled and self.schema_ok and self.write_enabled):
            self._log("ERROR", "update_status", "Notion not ready")
            return False
        ok, errs = self._validate_task_fields("x", status, None, None, None)
        if not ok:
            self._log("ERROR", "update_status", "Validation failed", {"errors": errs})
            return False

        st = self.prop_names.get("Status", "Status")
        up = self.prop_names.get("Updated at", "Updated at")
        props = {
            st: {"status": {"name": status}},
            up: {"date": {"start": self._now_iso()}},
        }
        payload = {"properties": props}
        ok, resp, status_code = self._request("PATCH", f"/pages/{task_id}", payload)
        self._log_request("update_status", "PATCH", f"/pages/{task_id}", payload, ok, status_code, resp)
        if not ok:
            self.last_error = f"Status update failed (HTTP {status_code})"
        return ok

    def update_task_properties(self, task_id: str, props: Dict[str, Any]) -> bool:
        if not (self.enabled and self.schema_ok and self.write_enabled):
            self._log("ERROR", "update_props", "Notion not ready")
            return False

        title = props.get("task_name") or props.get("title")
        status = props.get("status")
        priority = props.get("priority")
        effort = props.get("effort_level")
        summary = props.get("summary")
        due_raw = props.get("due_date") or props.get("due")
        due = self._normalize_date(due_raw) if due_raw else None

        ok, errs = self._validate_task_fields(title or "x", status, priority, effort, due)
        if not ok:
            self._log("ERROR", "update_props", "Validation failed", {"errors": errs})
            return False

        tn = self.prop_names.get("Task Name", "Task Name")
        st = self.prop_names.get("Status", "Status")
        pr = self.prop_names.get("Priority", "Priority")
        du = self.prop_names.get("Due date", "Due date")
        up = self.prop_names.get("Updated at", "Updated at")
        ef = self.prop_names.get("Effort level", "Effort level")
        sm = self.prop_names.get("Summary", "Summary")

        out: Dict[str, Any] = {up: {"date": {"start": self._now_iso()}}}
        if title is not None:
            out[tn] = {"title": [{"text": {"content": str(title)}}]}
        if status is not None:
            out[st] = {"status": {"name": status} if status else None}
        if priority is not None:
            out[pr] = {"select": {"name": priority} if priority else None}
        if effort is not None:
            out[ef] = {"select": {"name": effort} if effort else None}
        if summary is not None:
            out[sm] = {
                "rich_text": [{"text": {"content": str(summary)}}] if summary else []
            }
        if due_raw is not None:
            out[du] = {"date": {"start": due} if due else None}

        payload = {"properties": out}
        ok, resp, status_code = self._request("PATCH", f"/pages/{task_id}", payload)
        self._log_request("update_props", "PATCH", f"/pages/{task_id}", payload, ok, status_code, resp)
        if not ok:
            self.last_error = f"Update failed (HTTP {status_code})"
        return ok

    def update_task(self, task_id: str, props: Dict[str, Any]) -> bool:
        return self.update_task_properties(task_id, props)

    def delete_task(self, task_id: str) -> bool:
        if not (self.enabled and self.write_enabled):
            self._log("ERROR", "delete_task", "Notion not ready")
            return False
        payload = {"archived": True}
        ok, resp, status_code = self._request("PATCH", f"/pages/{task_id}", payload)
        self._log_request("delete_task", "PATCH", f"/pages/{task_id}", payload, ok, status_code, resp)
        if not ok:
            self.last_error = f"Delete failed (HTTP {status_code})"
        return ok

    def fetch_all_tasks(self) -> Optional[List[Dict[str, Any]]]:
        if not (self.enabled and self.schema_ok):
            self._log("ERROR", "fetch_all_tasks", "Notion not ready")
            return None

        path = f"/data_sources/{self.data_source_id}/query" if self.data_source_id else f"/databases/{self.database_id}/query"
        payload: Dict[str, Any] = {
            "page_size": 100,
            "sorts": [{"property": "Updated at", "direction": "descending"}],
        }

        results: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            if cursor:
                payload["start_cursor"] = cursor
            ok, resp, status_code = self._request("POST", path, payload)
            self._log_request("query", "POST", path, payload, ok, status_code, resp)
            if not ok:
                return None
            pages = resp.get("results") or []
            for p in pages:
                if p.get("archived"):
                    continue
                results.append(self._page_to_task_dict(p))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
            if not cursor:
                break
            time.sleep(0.05)

        # assign positions based on order
        for i, t in enumerate(results):
            t["position"] = i + 1
        return results

    def fetch_tasks(self) -> Optional[List[Dict[str, Any]]]:
        return self.fetch_all_tasks()

    def fetch_tasks_by_status(self, status: str) -> Optional[List[Dict[str, Any]]]:
        tasks = self.fetch_all_tasks()
        if tasks is None:
            return None
        return [t for t in tasks if t.get("status") == status]

    def fetch_completed_topics(self) -> List[str]:
        tasks = self.fetch_tasks_by_status(STATUS_DONE) or []
        return [t.get("task_name") for t in tasks if t.get("task_name")]

    def append_study_log(self, text: str) -> bool:
        if not self.log_enabled:
            self._log("WARN", "append_study_log", "Study log page not configured")
            return False
        payload = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": text}}
                        ]
                    },
                }
            ]
        }
        ok, resp, status_code = self._request(
            "PATCH", f"/blocks/{self.study_log_page_id}/children", payload
        )
        self._log_request(
            "append_log",
            "PATCH",
            f"/blocks/{self.study_log_page_id}/children",
            payload,
            ok,
            status_code,
            resp,
        )
        return ok

    # ── Schema changes ────────────────────────────────────────────────────

    def add_column(self, name: str, prop_type: str, options: Optional[List[str]] = None) -> bool:
        if not (self.enabled and self.write_enabled):
            return False
        if prop_type in {"status", "title"}:
            self._log("ERROR", "add_column", f"Property type not supported: {prop_type}")
            return False
        # Map logical name to actual if present
        actual_name = self.prop_names.get(name, name)

        schema: Dict[str, Any] = {"type": prop_type, prop_type: {}}
        if prop_type == "select":
            schema[prop_type]["options"] = [{"name": o} for o in (options or [])]
        elif prop_type == "date":
            schema[prop_type] = {}
        elif prop_type == "rich_text":
            schema[prop_type] = {}

        payload = {"properties": {actual_name: schema}}
        path = f"/data_sources/{self.data_source_id}" if self.data_source_id else f"/databases/{self.database_id}"
        ok, resp, status_code = self._request("PATCH", path, payload)
        self._log_request("add_column", "PATCH", path, payload, ok, status_code, resp)
        if ok:
            self.refresh_schema()
        return ok

    def delete_column(self, name: str) -> bool:
        if not (self.enabled and self.write_enabled):
            return False
        actual_name = self.prop_names.get(name, name)
        payload = {"properties": {actual_name: None}}
        path = f"/data_sources/{self.data_source_id}" if self.data_source_id else f"/databases/{self.database_id}"
        ok, resp, status_code = self._request("PATCH", path, payload)
        self._log_request("delete_column", "PATCH", path, payload, ok, status_code, resp)
        if ok:
            self.refresh_schema()
        return ok

    # ── Extractors ─────────────────────────────────────────────────────────

    @staticmethod
    def get_task_title(task_dict: Dict[str, Any]) -> str:
        return task_dict.get("task_name", "") or ""

    @staticmethod
    def get_task_status(task_dict: Dict[str, Any]) -> str:
        return task_dict.get("status", STATUS_NOT_STARTED) or STATUS_NOT_STARTED

    # ── Internal mapping ───────────────────────────────────────────────────

    def _page_to_task_dict(self, page: Dict[str, Any]) -> Dict[str, Any]:
        props = page.get("properties", {}) or {}
        tn = self.prop_names.get("Task Name", "Task Name")
        st = self.prop_names.get("Status", "Status")
        pr = self.prop_names.get("Priority", "Priority")
        ef = self.prop_names.get("Effort level", "Effort level")
        sm = self.prop_names.get("Summary", "Summary")
        du = self.prop_names.get("Due date", "Due date")
        up = self.prop_names.get("Updated at", "Updated at")

        title_prop = props.get(tn, {})
        status_prop = props.get(st, {})
        priority_prop = props.get(pr, {})
        effort_prop = props.get(ef, {})
        summary_prop = props.get(sm, {})
        due_prop = props.get(du, {})
        updated_prop = props.get(up, {})

        title = self._plain_text(title_prop.get("title", []) or [])
        status = (status_prop.get("status") or {}).get("name", "")
        priority = (priority_prop.get("select") or {}).get("name", "")
        effort = (effort_prop.get("select") or {}).get("name", "")
        summary = self._plain_text(summary_prop.get("rich_text", []) or [])
        due = (due_prop.get("date") or {}).get("start", "")
        updated = (updated_prop.get("date") or {}).get("start", "")

        return {
            "id": page.get("id"),
            "task_name": title,
            "status": status or STATUS_NOT_STARTED,
            "priority": priority or "Medium",
            "effort_level": effort or "",
            "summary": summary or "",
            "due_date": due or "",
            "due": due or "",
            "position": 0,
            "archived": bool(page.get("archived")),
            "created_at": page.get("created_time", ""),
            "updated_at": updated or page.get("last_edited_time", ""),
        }

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
