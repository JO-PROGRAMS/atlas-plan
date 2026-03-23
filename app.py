#!/usr/bin/env python3
"""
Atlas — FastAPI Web Server
==========================
Replaces Flask + Notion with FastAPI + local SQLite task database.

Run:
    pip install fastapi uvicorn sqlalchemy pydantic
    uvicorn app:app --reload --port 5000

Open: http://localhost:5000
"""

from __future__ import annotations

import collections
import csv
import io
import json
import os
import queue
import sys
import threading
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

sys.path.insert(0, os.path.dirname(__file__))

try:
    from agent import (
        AtlasAgent, ConfigManager, GeminiClient,
        LocalTaskDB, MemorySystem, AppConfig,
        load_personality, save_personality,
        user_custom_command, classify_intent,
        STATUS_DONE, STATUS_NOT_STARTED, HISTORY_FILE,
        _DEBUG_LOG, _dbg, local_now, fmt_local,
    )
    from backend.notion_client import NotionClient
    from backend.task_service import TaskService
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"[Server] Import error: {e}")
    AGENT_AVAILABLE = False
    _DEBUG_LOG = collections.deque(maxlen=200)
    def _dbg(*a, **k): pass
    def local_now(): return datetime.now()
    def fmt_local(f="%H:%M"): return datetime.now().strftime(f)

try:
    from backend.database import init_db, DB_PATH
    from backend.router import router as tasks_router
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"[Server] Backend import error: {e}")
    BACKEND_AVAILABLE = False
    DB_PATH = "atlas_tasks.db"

# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="Atlas AI Study Planner",
    version="5.0",
    description="Local-first AI study planner with optional Notion data source.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if BACKEND_AVAILABLE:
    app.include_router(tasks_router)

# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup():
    if BACKEND_AVAILABLE:
        init_db()
        print("[Server] ✓ SQLite database initialised")
    init_atlas()

# =============================================================================
# STATE
# =============================================================================

config_manager: Optional[Any]       = None
agent:          Optional[AtlasAgent] = None
_NOTIFICATIONS: collections.deque   = collections.deque(maxlen=50)


def push_notif(title: str, body: str, level: str = "info") -> None:
    _NOTIFICATIONS.append({
        "id":    int(datetime.now().timestamp() * 1000),
        "ts":    local_now().strftime("%H:%M"),
        "title": title,
        "body":  body,
        "level": level,
        "read":  False,
    })


def init_atlas() -> None:
    global config_manager, agent
    if not AGENT_AVAILABLE:
        return
    try:
        config_manager = ConfigManager()
        cfg   = config_manager.config
        gem   = GeminiClient(cfg.gemini_api_key, cfg.model_name)
        if not cfg.study_lists:
            cfg.study_lists = AppConfig().study_lists
        idx = max(0, min(cfg.active_study_list_index, len(cfg.study_lists) - 1))
        space = cfg.study_lists[idx]
        local_db = LocalTaskDB()
        notion = NotionClient(cfg.notion_token, space.database_id, space.study_log_page_id, logger=_dbg)
        service = TaskService(cfg.data_source, notion, local_db, logger=_dbg)
        agent = AtlasAgent(config=cfg, gemini=gem, db=service)
        _dbg("INFO", "server", "Atlas initialised", {"model": cfg.model_name, "data_source": cfg.data_source})
        push_notif("Atlas ready", f"{service.effective_source().upper()} · {cfg.model_name}", "success")
        print(f"[Server] ✓ Atlas ready  model={cfg.model_name} source={service.effective_source()}")
    except Exception as e:
        _dbg("ERROR", "server", f"Init error: {e}")
        push_notif("Init failed", str(e), "error")
        agent = None

# =============================================================================
# UI
# =============================================================================

_HTML_PATH = os.path.join(os.path.dirname(__file__), "index.html")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    try:
        with open(_HTML_PATH, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>index.html not found</h1>",
            status_code=404,
        )

# =============================================================================
# STATUS
# =============================================================================

@app.get("/api/status")
async def api_status():
    task_cnt = 0
    svc_status: Dict[str, Any] = {}
    if agent:
        try:
            task_cnt = len(agent.db.fetch_all_tasks())
            if hasattr(agent.db, "status"):
                svc_status = agent.db.status()
        except Exception:
            pass
    return {
        "agent":      agent is not None,
        "db":         BACKEND_AVAILABLE,
        "db_path":    str(DB_PATH),
        "model":      config_manager.config.model_name if config_manager else "—",
        "date":       date.today().isoformat(),
        "local_time": fmt_local("%Y-%m-%d %H:%M"),
        "task_count": task_cnt,
        "data_source": svc_status.get("data_source", "local"),
        "effective_source": svc_status.get("effective_source", "local"),
        "notion_ready": svc_status.get("notion_ready", False),
        "last_fallback": svc_status.get("last_fallback"),
        "notion_last_error": svc_status.get("notion_last_error"),
    }

# =============================================================================
# CHAT — SSE
# =============================================================================

@app.post("/api/chat")
async def api_chat(request: Request):
    body        = await request.json()
    user_prompt = (body.get("prompt") or "").strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="empty prompt")

    q: queue.Queue = queue.Queue()

    def worker():
        if not agent:
            q.put(("error", "Atlas not initialised. Check config.json and restart."))
            q.put(("done", {}))
            return

        custom = user_custom_command(user_prompt, agent)
        if custom is not None:
            q.put(("chunk", custom))
            q.put(("done", {}))
            return

        def cb(msg: str):
            q.put(("step", msg))

        try:
            response, log = agent.handle_prompt(user_prompt, status_cb=cb)
        except Exception as e:
            response, log = f"Error: {e}", [str(e)]
            _dbg("ERROR", "chat", str(e))

        try:
            tasks = agent.db.fetch_all_tasks()
            hi = [t["task_name"] for t in tasks
                  if t.get("priority") == "High"
                  and t.get("status") == STATUS_NOT_STARTED]
            if hi:
                push_notif("⚡ High Priority", f"{hi[0]} — needs attention", "warning")
        except Exception:
            pass

        q.put(("chunk", response))
        q.put(("done", {"log": log}))

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            try:
                kind, payload = q.get(timeout=120)
            except queue.Empty:
                yield f"data: {json.dumps({'type':'error','text':'timeout'})}\n\n"
                break
            if kind == "step":
                yield f"data: {json.dumps({'type':'step','text':payload})}\n\n"
            elif kind == "chunk":
                yield f"data: {json.dumps({'type':'chunk','text':payload})}\n\n"
            elif kind == "error":
                yield f"data: {json.dumps({'type':'error','text':payload})}\n\n"
            elif kind == "done":
                for line in (payload.get("log") or []):
                    yield f"data: {json.dumps({'type':'log','text':line})}\n\n"
                yield f"data: {json.dumps({'type':'done'})}\n\n"
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# =============================================================================
# /api/tasks  — UI convenience wrappers
# Full CRUD REST lives at /tasks via the backend router
# =============================================================================

@app.get("/api/tasks")
async def api_tasks_list():
    if not agent:
        return JSONResponse([])
    tasks = agent.db.fetch_all_tasks()
    return JSONResponse([
        {
            "id":        t["id"],
            "title":     t["task_name"],
            "task_name": t["task_name"],
            "status":    t["status"],
            "priority":  t["priority"],
            "effort":    t.get("effort_level", ""),
            "due":       t.get("due", "") or t.get("due_date", ""),
            "summary":   t.get("summary", ""),
            "position":  t.get("position", 0),
        }
        for t in tasks
    ])


@app.patch("/api/tasks/{task_id}/status")
async def api_task_status(task_id: str, request: Request):
    body   = await request.json()
    status = (body.get("status") or "").strip()
    if not agent or not status:
        raise HTTPException(status_code=400, detail="missing status")
    ok = agent.db.update_task_status(task_id, status)
    if ok:
        push_notif("Task updated", f"Status → {status}", "success")
    return {"ok": ok, "source": agent.db.effective_source()}


@app.delete("/api/tasks/{task_id}/delete")
async def api_task_delete_compat(task_id: str):
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not ready")
    ok = agent.db.delete_task(task_id)
    if ok:
        push_notif("Task deleted", "Removed from task list", "info")
    return {"ok": ok, "source": agent.db.effective_source()}


@app.delete("/api/tasks/{task_id}")
async def api_task_delete(task_id: str):
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not ready")
    ok = agent.db.delete_task(task_id)
    if ok:
        push_notif("Task deleted", "Removed from task list", "info")
    return {"ok": ok, "source": agent.db.effective_source()}


@app.post("/api/tasks/reorder")
async def api_tasks_reorder(request: Request):
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not ready")
    body = await request.json()
    items = body.get("tasks") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="missing tasks")
    updated = agent.db.reorder_tasks(items)
    ok = updated > 0
    if ok:
        push_notif("Tasks reordered", f"{updated} task(s) updated", "success")
    return {"ok": ok, "updated": updated, "source": agent.db.effective_source()}

# =============================================================================
# MEMORY / HISTORY / DEBUG
# =============================================================================

@app.get("/api/memory")
async def api_memory():
    if not agent:
        return JSONResponse({})
    mem = agent.memory
    return {
        "patterns":        mem.patterns_summary(),
        "progress":        mem.progress_toward_a_star(),
        "completion_rate": round(mem.completion_rate() * 100),
        "history": [
            {
                "date":         d.date,
                "done":         len(d.completed_tasks),
                "missed":       len(d.missed_tasks),
                "completed":    d.completed_tasks[:6],
                "missed_tasks": d.missed_tasks[:4],
                "summary":      d.eod_summary[:200] if d.eod_summary else "",
            }
            for d in mem.daily_history(7)
        ],
    }


@app.get("/api/history")
async def api_history():
    if not agent:
        return JSONResponse([])
    return JSONResponse(agent.load_recent_history(20))


@app.get("/api/debug")
async def api_debug(n: int = 150, level: str = ""):
    entries = list(_DEBUG_LOG)[-min(n, 200):]
    if level:
        entries = [e for e in entries if e.get("level") == level]
    return JSONResponse(list(reversed(entries)))


@app.post("/api/debug/clear")
async def api_debug_clear():
    _DEBUG_LOG.clear()
    return {"ok": True}

# =============================================================================
# DB TEST  (replaces /api/notion/test)
# =============================================================================

@app.post("/api/db/test")
async def api_db_test():
    if not agent:
        return {"ok": False, "error": "Agent not initialised"}
    try:
        local = getattr(agent.db, "local", None) or agent.db
        tasks = local.fetch_all_tasks()
        push_notif("DB test", f"{len(tasks)} tasks in local DB", "success")
        return {
            "ok":         True,
            "task_count": len(tasks),
            "db_path":    str(DB_PATH),
            "schema":     local.schema_summary() if hasattr(local, "schema_summary") else {},
            "db_type":    "SQLite (local)",
        }
    except Exception as exc:
        _dbg("ERROR", "db_test", str(exc))
        return {"ok": False, "error": str(exc)}


@app.post("/api/notion/test")
async def api_notion_test_compat():
    if not agent:
        return {"ok": False, "error": "Agent not initialised"}
    notion = getattr(agent.db, "notion", None)
    if not notion:
        return {"ok": False, "error": "Notion client not configured"}
    try:
        ok = notion.refresh_schema()
        if not ok:
            return {"ok": False, "error": "Schema validation failed"}
        return {
            "ok": True,
            "schema": notion.schema_summary() if hasattr(notion, "schema_summary") else {},
            "data_source_id": getattr(notion, "data_source_id", None),
        }
    except Exception as exc:
        _dbg("ERROR", "notion_test", str(exc))
        return {"ok": False, "error": str(exc)}

# =============================================================================
# CONFIG
# =============================================================================

@app.get("/api/config")
async def api_config_get():
    if not config_manager:
        raise HTTPException(status_code=500, detail="no config manager")
    cfg = config_manager.config
    return {
        "gemini_api_key": cfg.gemini_api_key,
        "model_name":     cfg.model_name,
        "personality":    load_personality(),
        "notion_token":   cfg.notion_token,
        "study_lists":    [
            {
                "name": s.name,
                "database_id": s.database_id,
                "study_log_page_id": s.study_log_page_id,
            }
            for s in (cfg.study_lists or [])
        ],
        "active_index":   cfg.active_study_list_index,
        "data_source":    cfg.data_source,
    }


@app.post("/api/config")
async def api_config_post(request: Request):
    if not config_manager:
        raise HTTPException(status_code=500, detail="no config manager")
    d   = await request.json()
    cfg = config_manager.config
    if d.get("gemini_api_key"): cfg.gemini_api_key = d["gemini_api_key"]
    if d.get("model_name"):     cfg.model_name     = d["model_name"]
    if d.get("personality"):    save_personality(d["personality"])
    if "notion_token" in d:
        cfg.notion_token = d.get("notion_token") or ""
    if "data_source" in d:
        ds = (d.get("data_source") or "local").lower()
        if ds not in {"local", "notion"}:
            ds = "local"
        cfg.data_source = ds
    if "study_lists" in d and isinstance(d["study_lists"], list) and d["study_lists"]:
        cls = type(cfg.study_lists[0]) if cfg.study_lists else type(AppConfig().study_lists[0])
        cfg.study_lists = [
            cls(
                name=x.get("name", "Space"),
                database_id=x.get("database_id", ""),
                study_log_page_id=x.get("study_log_page_id", ""),
            )
            for x in d["study_lists"]
        ]
    if "active_index" in d:
        try:
            cfg.active_study_list_index = int(d["active_index"])
        except Exception:
            pass
    config_manager.save(cfg)
    init_atlas()
    push_notif("Settings saved", "Reconnecting…", "info")
    return {"ok": True}

# =============================================================================
# NOTIFICATIONS
# =============================================================================

@app.get("/api/notifications")
async def api_notifications():
    return JSONResponse(list(_NOTIFICATIONS))


@app.post("/api/notifications/read")
async def api_notif_read():
    for n in _NOTIFICATIONS:
        n["read"] = True
    return {"ok": True}

# =============================================================================
# EXPORT
# =============================================================================

@app.get("/api/export/json")
async def api_export_json():
    tasks = agent.db.fetch_all_tasks() if agent else []
    out   = [
        {
            "title":    t["task_name"],
            "status":   t["status"],
            "priority": t["priority"],
            "effort":   t.get("effort_level", ""),
            "due":      t.get("due", ""),
            "summary":  t.get("summary", ""),
        }
        for t in tasks
    ]
    return Response(
        content=json.dumps(out, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="atlas_tasks_{date.today()}.json"'},
    )


@app.get("/api/export/csv")
async def api_export_csv():
    tasks = agent.db.fetch_all_tasks() if agent else []
    buf   = io.StringIO()
    w     = csv.writer(buf)
    w.writerow(["title", "status", "priority", "effort", "due", "summary"])
    for t in tasks:
        w.writerow([
            t["task_name"], t["status"], t["priority"],
            t.get("effort_level", ""), t.get("due", ""), t.get("summary", ""),
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="atlas_tasks_{date.today()}.csv"'},
    )

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  ✦ Atlas v5 (FastAPI + SQLite)  →  http://localhost:{port}")
    print(f"  ✦ API docs                     →  http://localhost:{port}/api/docs\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
