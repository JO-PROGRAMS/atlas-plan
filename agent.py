#!/usr/bin/env python3
"""
Atlas - Autonomous AI Study & Task Planner
==========================================
Version 4.0

New in v4:
  • Precise due dates with exact hours + minutes
  • Persistent memory system (daily logs, patterns, progress toward A*)
  • /memory /patterns /progress CLI+GUI commands
  • Intelligent plan generation from short prompts
  • Automatic task importance + priority analysis
  • Effort level estimation per task
  • Auto-generated one-sentence task summaries
  • Workload balancing + smart scheduling
  • Transparent reasoning display (Thinking / Planning / Generating / Applying)
  • Completely redesigned GUI – dark, sleek, professional

Usage:
    python agent.py           # GUI if Tkinter available, else CLI
    python agent.py --gui
    python agent.py --cli
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

def local_now() -> datetime:
    """Return current local time (timezone-aware if possible, else naive)."""
    try:
        import zoneinfo
        from zoneinfo import ZoneInfo
        import time as _time
        tz = ZoneInfo(_time.tzname[0] if _time.tzname else "UTC")
        return datetime.now(tz)
    except Exception:
        return datetime.now()

def fmt_local(fmt: str = "%Y-%m-%d %H:%M") -> str:
    return local_now().strftime(fmt)

def local_date_str() -> str:
    return local_now().strftime("%Y-%m-%d")

def local_iso_time(hour: int = 9, minute: int = 0) -> str:
    """Return today's date with given time as ISO8601 string."""
    d = local_now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return d.strftime("%Y-%m-%dT%H:%M:00")


try:
    import tkinter as tk
    from tkinter import scrolledtext, messagebox, ttk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

import requests

from backend.local_db import LocalDBClient
from backend.notion_client import NotionClient
from backend.task_service import TaskService

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

try:
    from google import genai
except ImportError:
    genai = None


# =============================================================================
# CONSTANTS
# =============================================================================

CONFIG_PATH          = "config.json"
PERSONALITY_PATH     = "personality.txt"
HISTORY_FILE         = "session_history.jsonl"
MEMORY_FILE          = "atlas_memory.jsonl"

STATUS_NOT_STARTED = "Not started"
STATUS_IN_PROGRESS = "In progress"
STATUS_DONE        = "Done"
STATUS_PLANNED     = "Planned"

VALID_STATUSES   = {STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_PLANNED}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_EFFORTS    = {"Small", "Medium", "Large"}

# GUI colour palette – dark obsidian theme
C = {
    "bg":        "#0d0f14",
    "surface":   "#151820",
    "surface2":  "#1c2030",
    "border":    "#252a3a",
    "accent":    "#4f8ef7",
    "accent2":   "#7c5cbf",
    "green":     "#3dd68c",
    "orange":    "#f5a623",
    "red":       "#e05252",
    "text":      "#e8eaf0",
    "muted":     "#6b7394",
    "heading":   "#ffffff",
}

DEFAULT_PERSONALITY = textwrap.dedent("""
    You are Atlas, a world-class AI study coach and task planner
    for a highly motivated 16-year-old student targeting an A* in mathematics.

    Core principles:
    - Break every goal into small, concrete, time-boxed tasks.
    - Prioritise understanding and intuition over rote memorisation.
    - Be honest about difficulty – don't sugarcoat hard topics.
    - Balance ambition with sustainability: avoid burnout.
    - Reference past performance patterns to make smarter plans.
    - Your goal is to get this student an A* in maths.
""").strip()

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StudyTask:
    title: str
    source_prompt: str
    created_at: str
    description: str  = ""
    due_date: str     = ""          # ISO 8601 with time: "2026-03-11T14:30:00"
    effort_level: str = ""          # Small | Medium | Large
    priority: str     = "Medium"    # Low | Medium | High
    status: str       = STATUS_NOT_STARTED
    summary: str      = ""
    task_type: str    = ""


@dataclass
class ActionItem:
    action: str       # create_task | update_task | delete_task | update_status |
                      # add_column | delete_column | append_log | no_action
    target: str
    payload: Dict[str, Any]
    status: str = "pending"
    error:  str = ""


@dataclass
class ActionPlan:
    timestamp: str
    user_prompt: str
    intent: str
    needs_action: bool
    actions: List[ActionItem]
    atlas_response: str  = ""
    reasoning: str       = ""


@dataclass
class InteractionRecord:
    timestamp: str
    user_prompt: str
    atlas_response: str
    tasks: List[StudyTask]
    actions_taken: List[str]


@dataclass
class DailyMemory:
    """One day's study record stored in atlas_memory.jsonl."""
    date: str                          # "2026-03-11"
    completed_tasks: List[str]
    missed_tasks: List[str]
    session_count: int
    total_prompts: int
    patterns: List[str]                # short insight strings
    eod_summary: str


@dataclass
class StudyListConfig:
    name: str              = "Default Study Space"
    database_id: str       = ""
    study_log_page_id: str = ""


@dataclass
class AppConfig:
    gemini_api_key: str     = ""
    model_name: str         = "gemini-1.5-flash"
    personality: str        = field(default_factory=lambda: DEFAULT_PERSONALITY)
    notion_token: str       = ""
    data_source: str        = "local"
    study_lists: List[StudyListConfig] = field(
        default_factory=lambda: [StudyListConfig()]
    )
    active_study_list_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gemini_api_key": self.gemini_api_key,
            "model_name": self.model_name,
            "personality": self.personality,
            "notion_token": self.notion_token,
            "data_source": self.data_source,
            "study_lists": [asdict(s) for s in self.study_lists],
            "active_study_list_index": self.active_study_list_index,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AppConfig:
        lists = [
            StudyListConfig(
                name=x.get("name", "Space"),
                database_id=x.get("database_id", ""),
                study_log_page_id=x.get("study_log_page_id", ""),
            )
            for x in (d.get("study_lists") or [])
        ] or [StudyListConfig()]
        ds = (d.get("data_source") or "local").lower()
        if ds not in {"local", "notion"}:
            ds = "local"
        return cls(
            gemini_api_key=d.get("gemini_api_key", ""),
            model_name=d.get("model_name", "gemini-1.5-flash"),
            personality=d.get("personality") or DEFAULT_PERSONALITY,
            notion_token=d.get("notion_token", ""),
            data_source=ds,
            study_lists=lists,
            active_study_list_index=int(d.get("active_study_list_index", 0)),
        )


# =============================================================================
# CONFIG + PERSONALITY
# =============================================================================

class ConfigManager:
    def __init__(self, path: str = CONFIG_PATH) -> None:
        self.path   = path
        self.config = self._load()

    def _load(self) -> AppConfig:
        if not os.path.exists(self.path):
            cfg = AppConfig()
            self._apply_env_overrides(cfg)
            self.save(cfg)
            return cfg
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                cfg = AppConfig.from_dict(json.load(f))
                self._apply_env_overrides(cfg)
                return cfg
        except Exception as e:
            print(f"[Config] {e} — using defaults.")
            cfg = AppConfig()
            self._apply_env_overrides(cfg)
            return cfg

    def _apply_env_overrides(self, cfg: AppConfig) -> None:
        gemini = os.getenv("GEMINI") or os.getenv("GEMINI_API_KEY")
        notion = os.getenv("NOTION_AUTH") or os.getenv("NOTION_TOKEN")
        db_id = os.getenv("DATABASE_ID") or os.getenv("NOTION_DATABASE_ID")
        page_id = os.getenv("PAGE_ID") or os.getenv("STUDY_LOG_PAGE_ID")

        if gemini:
            cfg.gemini_api_key = gemini
        if notion:
            cfg.notion_token = notion

        if not cfg.study_lists:
            cfg.study_lists = [StudyListConfig()]

        if db_id:
            cfg.study_lists[0].database_id = db_id
        if page_id:
            cfg.study_lists[0].study_log_page_id = page_id

    def save(self, cfg: Optional[AppConfig] = None) -> None:
        if cfg:
            self.config = cfg
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[Config] Write error: {e}")


def load_personality() -> str:
    try:
        if os.path.exists(PERSONALITY_PATH):
            t = open(PERSONALITY_PATH, "r", encoding="utf-8").read().strip()
            if t:
                return t
    except Exception:
        pass
    return DEFAULT_PERSONALITY


def save_personality(text: str) -> None:
    try:
        open(PERSONALITY_PATH, "w", encoding="utf-8").write(text)
    except Exception as e:
        print(f"[Personality] {e}")


# =============================================================================
# MEMORY SYSTEM
# =============================================================================

class MemorySystem:
    """
    Persistent study memory.
    Stores DailyMemory records in atlas_memory.jsonl.
    Provides pattern analysis and progress tracking toward A*.
    """

    def __init__(self, path: str = MEMORY_FILE) -> None:
        self.path = path

    # ── I/O ───────────────────────────────────────────────────────────────

    def load_all(self) -> List[DailyMemory]:
        records = []
        if not os.path.exists(self.path):
            return records
        try:
            for line in open(self.path, "r", encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(DailyMemory(**d))
                except Exception:
                    pass
        except Exception as e:
            print(f"[Memory] Read error: {e}")
        return records

    def load_today(self) -> Optional[DailyMemory]:
        today = date.today().isoformat()
        for m in self.load_all():
            if m.date == today:
                return m
        return None

    def save_day(self, memory: DailyMemory) -> None:
        """Upsert today's memory record."""
        today   = date.today().isoformat()
        records = self.load_all()
        # Remove existing entry for today if any
        records = [r for r in records if r.date != today]
        records.append(memory)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                for r in records:
                    json.dump(asdict(r), f)
                    f.write("\n")
        except Exception as e:
            print(f"[Memory] Write error: {e}")

    def record_session(self, completed: List[str], missed: List[str],
                       prompt_count: int = 1) -> None:
        """Update today's memory with latest task outcomes."""
        today = self.load_today() or DailyMemory(
            date=date.today().isoformat(),
            completed_tasks=[], missed_tasks=[],
            session_count=0, total_prompts=0,
            patterns=[], eod_summary=""
        )
        today.completed_tasks = list(set(today.completed_tasks + completed))
        today.missed_tasks    = list(set(today.missed_tasks + missed) - set(completed))
        today.session_count  += 1
        today.total_prompts  += prompt_count
        self.save_day(today)

    def set_eod_summary(self, summary: str) -> None:
        today = self.load_today() or DailyMemory(
            date=date.today().isoformat(),
            completed_tasks=[], missed_tasks=[],
            session_count=0, total_prompts=0,
            patterns=[], eod_summary=""
        )
        today.eod_summary = summary
        self.save_day(today)

    # ── Analysis ──────────────────────────────────────────────────────────

    def daily_history(self, n: int = 7) -> List[DailyMemory]:
        return self.load_all()[-n:]

    def completion_rate(self, n: int = 7) -> float:
        """Return average task completion rate over the last n days (0–1)."""
        days = self.daily_history(n)
        if not days:
            return 0.0
        rates = []
        for d in days:
            total = len(d.completed_tasks) + len(d.missed_tasks)
            rates.append(len(d.completed_tasks) / total if total else 0.0)
        return sum(rates) / len(rates)

    def patterns_summary(self) -> str:
        """Plain-text summary of study patterns from recent memory."""
        days = self.daily_history(14)
        if not days:
            return "No memory yet – start studying to build your history."
        lines = []
        total_done   = sum(len(d.completed_tasks) for d in days)
        total_missed = sum(len(d.missed_tasks) for d in days)
        rate         = self.completion_rate()
        lines.append(f"Last {len(days)} days:  {total_done} tasks done, {total_missed} missed  ({rate*100:.0f}% completion)")

        # Streak
        streak = 0
        for d in reversed(days):
            if d.completed_tasks:
                streak += 1
            else:
                break
        if streak:
            lines.append(f"Current streak: {streak} day(s) with at least one completed task.")

        # Most missed topics
        missed_counts: Dict[str, int] = defaultdict(int)
        for d in days:
            for t in d.missed_tasks:
                missed_counts[t] += 1
        if missed_counts:
            top = sorted(missed_counts.items(), key=lambda x: -x[1])[:3]
            lines.append("Most-missed tasks: " + ", ".join(f'"{t}" ({c}x)' for t, c in top))

        return "\n".join(lines)

    def progress_toward_a_star(self) -> str:
        """Qualitative progress report toward A* in maths."""
        rate = self.completion_rate(14)
        days = self.daily_history(14)
        active_days = sum(1 for d in days if d.completed_tasks)
        total_done  = sum(len(d.completed_tasks) for d in days)

        if rate >= 0.85 and active_days >= 10:
            level = "EXCELLENT – on track for A*"
            advice = "Maintain consistency and start timed past papers."
        elif rate >= 0.65:
            level = "GOOD – progressing steadily"
            advice = "Reduce missed sessions and focus on weakest topics."
        elif rate >= 0.40:
            level = "NEEDS IMPROVEMENT"
            advice = "Increase daily study sessions. Target 2 tasks minimum per day."
        else:
            level = "CRITICAL – at risk of not achieving A*"
            advice = "Urgent: re-establish a daily study routine immediately."

        lines = [
            f"Progress toward A* in Maths",
            f"{'─'*40}",
            f"Status       : {level}",
            f"Completion   : {rate*100:.0f}% (last 14 days)",
            f"Active days  : {active_days}/14",
            f"Tasks done   : {total_done}",
            f"Advice       : {advice}",
        ]
        return "\n".join(lines)

    def context_for_planner(self) -> str:
        """Return a compact memory context string for the action planner."""
        days = self.daily_history(5)
        if not days:
            return "No previous memory."
        lines = ["Recent study memory (last 5 days):"]
        for d in days:
            done_str   = ", ".join(d.completed_tasks[:4]) or "none"
            missed_str = ", ".join(d.missed_tasks[:3]) or "none"
            lines.append(
                f"  {d.date}: done=[{done_str}]  missed=[{missed_str}]"
            )
        lines.append(f"Overall completion rate: {self.completion_rate()*100:.0f}%")
        return "\n".join(lines)



# =============================================================================
# LOCAL TASK DB  (SQLite wrapper)
# =============================================================================

import collections as _collections
_DEBUG_LOG: _collections.deque = _collections.deque(maxlen=200)

def _dbg(level: str, source: str, msg: str, data: Any = None) -> None:
    entry = {
        "ts":     datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "level":  level,
        "source": source,
        "msg":    msg,
        "data":   data,
    }
    _DEBUG_LOG.append(entry)
    prefix = {"ERROR": "✗", "WARN": "⚠", "DB": "◈", "GEMINI": "G", "NOTION": "N", "SERVICE": "S"}.get(level, "·")
    print(f"[{prefix} {source}] {msg}")


class LocalTaskDB(LocalDBClient):
    """Compatibility wrapper around the new LocalDBClient."""

    def __init__(self) -> None:
        super().__init__(logger=_dbg)

# =============================================================================
# GEMINI CLIENT
# =============================================================================

class GeminiClient:
    _RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, model_name: str) -> None:
        if genai is None:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
        if not api_key:
            raise ValueError("Gemini API key missing.")
        self.client     = genai.Client(api_key=api_key)
        self.model_name = model_name or "gemini-1.5-flash"

    def generate(self, system_prompt: str, user_prompt: str,
                 retries: int = 3, delay: float = 4.0,
                 history: Optional[List[str]] = None) -> str:
        """
        Generate a response.
        history: optional list of alternating prior messages
                 ["user: ...", "atlas: ...", "user: ...", ...]
                 Injected between system prompt and current user message.
        """
        # Build prompt with conversation history to prevent NPC loop
        history_block = ""
        if history:
            recent = history[-6:]  # last 3 exchanges
            history_block = "\n\nRecent conversation:\n" + "\n".join(recent)

        combined = f"{system_prompt}{history_block}\n\nUser: {user_prompt}"
        _dbg("GEMINI", "generate", f"Prompt built ({len(combined)} chars)",
             {"history_turns": len(history) if history else 0})
        last_err = ""
        for attempt in range(1, retries + 1):
            try:
                r = self.client.models.generate_content(
                    model=self.model_name, contents=combined
                )
                result = getattr(r, "text", "") or ""
                _dbg("GEMINI", "generate", f"Response ({len(result)} chars)")
                return result
            except Exception as e:
                last_err = str(e)
                retryable = any(str(c) in last_err for c in self._RETRYABLE)
                if retryable and attempt < retries:
                    wait = delay * attempt
                    print(f"[Gemini] Transient error (attempt {attempt}/{retries}), retrying in {wait:.0f}s")
                    time.sleep(wait)
                else:
                    break
        _dbg("ERROR", "GeminiClient", f"Failed after {retries} attempts", {"error": last_err[:300]})
        if "503" in last_err or "UNAVAILABLE" in last_err:
            return "Gemini is temporarily unavailable. Please try again in a moment."
        if "429" in last_err or "quota" in last_err.lower():
            return "Gemini rate limit reached. Please wait a minute and try again."
        return f"Gemini error: {last_err}"

    def generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        raw = self.generate(system_prompt, user_prompt)
        if not raw or (raw.startswith("Gemini ") and ("unavailable" in raw.lower() or "error" in raw.lower())):
            _dbg("ERROR", "generate_json", f"Gemini error/empty: {raw[:120]}")
            return None
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        # Sometimes Gemini wraps with extra text before/after JSON
        # Try to extract the JSON object
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)
        try:
            result = json.loads(cleaned)
            _dbg("GEMINI", "generate_json", f"✓ Parsed JSON: intent={result.get('intent','?')} needs_action={result.get('needs_action','?')} actions={len(result.get('actions',[]))}")
            return result
        except json.JSONDecodeError as e:
            _dbg("ERROR", "generate_json", f"JSON parse failed: {e}", {"raw_first_500": raw[:500]})
            return None


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================

EOD_PHRASES = {
    "i'm done for the day", "im done for the day", "done for the day",
    "i am done for the day", "that's it for today", "thats it for today",
    "wrapping up", "end of day", "finished for today",
    "done studying", "done for today", "calling it a day",
}
QUESTION_STARTERS = (
    "what", "how", "why", "when", "where", "who", "which",
    "can you explain", "tell me", "what is", "what are", "explain",
)


def classify_intent(prompt: str) -> str:
    lower = prompt.lower().strip()
    if any(ph in lower for ph in EOD_PHRASES):
        return "end_of_day"
    if lower.endswith("?") or any(lower.startswith(s) for s in QUESTION_STARTERS):
        return "question"
    if any(w in lower for w in ("add column", "new column", "delete column", "remove column")):
        return "schema_change"
    if any(w in lower for w in ("mark", "done", "finished", "complete", "completed", "status")):
        return "status_update"
    if any(w in lower for w in ("update", "change", "edit", "revise", "modify")):
        return "revise_tasks"
    if any(w in lower for w in (
        "plan", "schedule", "task", "study", "todo", "to-do", "session",
        "add", "create", "help me", "i need to", "i want to", "lets",
        "maths", "math", "algebra", "calculus", "revision", "exam", "test",
        "homework", "practice", "exercise", "topic", "chapter",
    )):
        return "plan_tasks"
    return "general"


# =============================================================================
# INTELLIGENT ACTION PLANNER
# =============================================================================

PLANNER_SYSTEM_PROMPT = textwrap.dedent("""
    You are Atlas's intelligent action planner for a 16-year-old student targeting an A* in maths.

    RULES:
    1. Only include actions that are truly necessary.
    2. Never create a task that already exists with the same title.
    3. Prefer updating existing tasks over duplicating.
    4. For EVERY create_task action you MUST:
       a. Set a realistic due_date with exact time (ISO 8601: "YYYY-MM-DDThh:mm:00").
          Space tasks realistically across the day (09:00, 10:30, 14:00, 16:00, etc.).
          Use today's date unless the user specifies otherwise.
       b. Set priority based on importance analysis:
          - "High" for exam-critical topics, upcoming tests, or long-overdue tasks
          - "Medium" for regular study tasks
          - "Low" for optional/supplementary work
       c. Set effort_level based on estimated time/difficulty:
          - "Large" for 60+ min tasks or complex topics
          - "Medium" for 30–60 min tasks
          - "Small" for 15–30 min tasks or review tasks
       d. Write a one-sentence summary describing the task clearly.
       e. Distribute workload realistically – don't create 10 tasks in one hour.
    5. If the user gives a short vague prompt (e.g. "study maths"), expand it into
       3–6 specific, concrete, time-boxed tasks.
    6. Balance the schedule: mix high-effort and low-effort tasks.
    7. Reference past memory to avoid re-creating completed tasks.
    8. Use ONLY these action types:
         create_task | update_task | delete_task | update_status |
         add_column | delete_column | append_log | no_action

    STATUS: "Not started" | "In progress" | "Done" | "Planned"
    PRIORITY: "Low" | "Medium" | "High"
    EFFORT: "Small" | "Medium" | "Large"

    OUTPUT: pure JSON only, no markdown fences:
    {
      "intent": "<string>",
      "needs_action": true|false,
      "reasoning": "<explain your planning decisions>",
      "workload_note": "<brief note on how you balanced the schedule>",
      "actions": [
        {
          "action": "<type>",
          "target": "<human description>",
          "payload": {
            "title": "...",
            "status": "...",
            "priority": "...",
            "effort_level": "...",
            "summary": "<one sentence>",
            "due_date": "YYYY-MM-DDThh:mm:00",
            "task_type": "...",
            "description": "..."
          }
        }
      ],
      "response": "<warm, structured Atlas reply with the full plan>"
    }

    For update_task / update_status / delete_task: include page_id in payload.
    If needs_action is false, actions must be [].
""").strip()



# =============================================================================
# ACTION PLANNER
# =============================================================================

class ActionPlanner:
    def __init__(self, gemini: GeminiClient, db: TaskService,
                 memory: MemorySystem) -> None:
        self.gemini = gemini
        self.db     = db
        self.memory = memory

    def _build_context(self) -> str:
        tasks = self.db.fetch_all_tasks()
        lines = [
            f"Today (local): {local_date_str()} {fmt_local('%H:%M')} — use this date/time for all due dates",
            f"DB schema: {json.dumps(self.db.schema_summary())}",
            f"Total tasks: {len(tasks)}", ""
        ]
        for t in tasks[:30]:
            lines.append(
                f"  [{t['status']}] {t['task_name']} | priority={t['priority']} | id={t['id']}"
            )
        return "\n".join(lines)

    def plan(self, user_prompt: str, intent: str,
             history_context: str = "") -> ActionPlan:
        context    = self._build_context()
        memory_ctx = self.memory.context_for_planner()
        user_content = (
            f"Intent: {intent}\n"
            f"User prompt: {user_prompt}\n\n"
            f"Current task state:\n{context}\n\n"
            f"Study memory:\n{memory_ctx}\n\n"
            f"Recent session history:\n{history_context}"
        )
        raw = self.gemini.generate_json(PLANNER_SYSTEM_PROMPT, user_content)

        if not isinstance(raw, dict):
            time.sleep(2)
            fallback = self.gemini.generate(load_personality(), user_prompt)
            return ActionPlan(
                timestamp=datetime.utcnow().isoformat(),
                user_prompt=user_prompt, intent=intent,
                needs_action=False,
                actions=[ActionItem("no_action", "Planner unavailable", {})],
                atlas_response=fallback,
            )

        actions = [
            ActionItem(
                action=a.get("action", "no_action"),
                target=a.get("target", ""),
                payload=a.get("payload", {}),
            )
            for a in raw.get("actions", [])
        ]
        return ActionPlan(
            timestamp=datetime.utcnow().isoformat(),
            user_prompt=user_prompt,
            intent=raw.get("intent", intent),
            needs_action=bool(raw.get("needs_action", False)),
            actions=actions,
            atlas_response=raw.get("response", ""),
            reasoning=raw.get("reasoning", "") + "\n" + raw.get("workload_note", ""),
        )


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    def __init__(self, db: TaskService) -> None:
        self.db = db

    def execute(self, plan: ActionPlan) -> List[str]:
        log: List[str] = []
        if not plan.needs_action:
            log.append("  No DB changes required.")
            return log
        for item in plan.actions:
            if item.action == "no_action":
                item.status = "done"
                continue
            try:
                ok = self._run(item)
                item.status = "done" if ok else "failed"
                log.append(f"  {'✓' if ok else '✗'} [{item.action}] {item.target}")
            except Exception as e:
                item.status = "failed"
                item.error  = str(e)
                log.append(f"  ✗ [{item.action}] {item.target} → {e}")
        return log

    def _run(self, item: ActionItem) -> bool:
        p, act = item.payload, item.action
        s = LocalTaskDB._s

        if act == "create_task":
            task = StudyTask(
                title=s(p.get("title", "Untitled")),
                source_prompt=s(p.get("description", "")),
                created_at=datetime.utcnow().isoformat(),
                description=s(p.get("description", "")),
                due_date=s(p.get("due_date", "")),
                effort_level=s(p.get("effort_level", "")),
                priority=s(p.get("priority", "Medium")),
                status=s(p.get("status", STATUS_NOT_STARTED)),
                summary=s(p.get("summary", "")),
                task_type=s(p.get("task_type", "")),
            )
            pid = self.db.create_task(task)
            if pid:
                _dbg("DB", "executor", f"✓ create_task: {pid[:8]}")
            else:
                _dbg("ERROR", "executor", f"✗ create_task failed for '{task.title[:50]}'")
            return pid is not None

        if act in ("update_task", "update_status"):
            pid = s(p.get("page_id", "") or p.get("id", ""))
            if not pid:
                return False
            if act == "update_status":
                return self.db.update_task_status(pid, s(p.get("status", STATUS_IN_PROGRESS)))
            props: Dict[str, Any] = {}
            if "title" in p:      props["task_name"]    = s(p["title"])
            if "status" in p:     props["status"]       = s(p["status"])
            if "priority" in p:   props["priority"]     = s(p["priority"])
            if "effort_level" in p: props["effort_level"] = s(p["effort_level"])
            if "summary" in p:    props["summary"]      = s(p["summary"])
            if "due_date" in p:
                due = LocalTaskDB._format_due_date(s(p["due_date"]))
                if due:
                    props["due_date"] = due
            return self.db.update_task_properties(pid, props)

        if act == "delete_task":
            pid = s(p.get("page_id", "") or p.get("id", ""))
            return self.db.delete_task(pid) if pid else False

        if act == "append_log":
            self.db.append_study_log(s(p.get("text", item.target)))
            return True

        if act == "add_column":
            name = s(p.get("name") or p.get("column") or p.get("title"))
            col_type = s(p.get("type") or p.get("property_type") or p.get("column_type"))
            options = p.get("options") or p.get("select_options")
            if not name or not col_type:
                _dbg("ERROR", "executor", "add_column missing name/type", {"payload": p})
                return False
            return self.db.add_column(name, col_type, options if isinstance(options, list) else None)

        if act == "delete_column":
            name = s(p.get("name") or p.get("column") or p.get("title"))
            if not name:
                _dbg("ERROR", "executor", "delete_column missing name", {"payload": p})
                return False
            return self.db.delete_column(name)

        return False


# =============================================================================
# END-OF-DAY HANDLER
# =============================================================================

EOD_PROMPT = textwrap.dedent("""
    You are Atlas.  The student has finished studying for the day.
    Write a structured, warm end-of-day summary (max 20 lines):
    1. What was accomplished today (be specific).
    2. What was missed and why it matters.
    3. Top 3 priorities for tomorrow.
    4. One honest observation about today's study patterns.
    5. One motivating closing sentence.
""").strip()

DAILY_COLUMNS: set = set()   # no-op in local DB mode


class EndOfDayHandler:
    def __init__(self, gemini: GeminiClient, db: TaskService,
                 memory: MemorySystem) -> None:
        self.gemini = gemini
        self.db     = db
        self.memory = memory

    def run(self, history_context: str) -> Tuple[str, List[str]]:
        tasks = self.db.fetch_all_tasks()
        done, not_done = [], []
        for t in tasks:
            title  = t.get("task_name", "")
            status = t.get("status", "")
            (done if status == STATUS_DONE else not_done if title else []).append(title)

        context = (
            f"Tasks completed: {', '.join(done) or 'none'}\n"
            f"Tasks not completed: {', '.join(not_done) or 'none'}\n"
            f"Memory patterns: {self.memory.patterns_summary()}\n"
            f"Session history: {history_context}"
        )
        try:
            summary = self.gemini.generate(EOD_PROMPT, context)
        except Exception as e:
            summary = f"[EOD summary unavailable: {e}]"

        self.memory.record_session(done, not_done)
        self.memory.set_eod_summary(summary)
        self.db.append_study_log(f"END OF DAY {date.today()}: {summary[:400]}")
        return summary, [summary]


# =============================================================================
# ATLAS AGENT
# =============================================================================

class AtlasAgent:
    """Main orchestrator — routes tasks via TaskService."""

    def __init__(
        self,
        config: AppConfig,
        gemini: GeminiClient,
        db: TaskService,
        history_file: str = HISTORY_FILE,
    ) -> None:
        self.config       = config
        self.gemini       = gemini
        self.db           = db
        # Keep .notion as an alias so existing code that references agent.notion works
        self.notion       = db
        self.history_file = history_file
        self.memory       = MemorySystem()
        self.planner      = ActionPlanner(gemini, db, self.memory)
        self.executor     = ActionExecutor(db)
        self.eod          = EndOfDayHandler(gemini, db, self.memory)

    # ── History ───────────────────────────────────────────────────────────

    def load_recent_history(self, n: int = 10) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(self.history_file):
                return []
            records = []
            for line in open(self.history_file, "r", encoding="utf-8"):
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
            return records[-n:]
        except Exception as e:
            print(f"[History] {e}")
            return []

    def _history_context(self, n: int = 3) -> str:
        records = self.load_recent_history(n)
        if not records:
            return "(no history)"
        return "\n".join(
            f"[{r.get('timestamp','')[:16]}] {r.get('user_prompt','')[:80]}"
            for r in records
        )

    def _conversation_history(self, n: int = 6) -> List[str]:
        records = self.load_recent_history(n)
        lines = []
        for r in records:
            u = (r.get("user_prompt") or "").strip()[:200]
            a = (r.get("atlas_response") or "").strip()[:300]
            if u: lines.append(f"User: {u}")
            if a: lines.append(f"Atlas: {a}")
        return lines

    def _last_atlas_response(self) -> str:
        records = self.load_recent_history(1)
        if not records:
            return ""
        return (records[-1].get("atlas_response") or "").strip()

    def _save(self, record: InteractionRecord) -> None:
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                json.dump({
                    "timestamp":     record.timestamp,
                    "user_prompt":   record.user_prompt,
                    "atlas_response": record.atlas_response,
                    "tasks":         [asdict(t) for t in record.tasks],
                    "actions_taken": record.actions_taken,
                }, f)
                f.write("\n")
        except Exception as e:
            print(f"[History] {e}")

    def _enrich_personality(self, base: str, completed: List[str]) -> str:
        if not completed:
            return base
        topics = "; ".join(sorted(set(completed))[:15])
        return base + f"\n\nCompleted topics: {topics}\n→ Focus on weaker/uncovered topics."

    # ── Main entry point ──────────────────────────────────────────────────

    def handle_prompt(
        self, user_prompt: str,
        status_cb: Optional[Callable[[str], None]] = None
    ) -> Tuple[str, List[str]]:
        def step(msg: str) -> None:
            print(f"[Atlas] {msg}")
            if status_cb:
                status_cb(msg)

        step("Thinking...")
        intent = classify_intent(user_prompt)
        step(f"Intent → {intent}")

        if intent == "end_of_day":
            step("Generating end-of-day summary...")
            summary, log = self.eod.run(self._history_context())
            self._save(InteractionRecord(
                timestamp=datetime.utcnow().isoformat(),
                user_prompt=user_prompt, atlas_response=summary,
                tasks=[], actions_taken=log,
            ))
            step("Done.")
            return summary, log

        if intent in ("question", "general"):
            step("Answering...")
            completed = self.db.fetch_completed_topics()
            system    = self._enrich_personality(load_personality(), completed)
            history   = self._conversation_history(n=6)
            last_resp = self._last_atlas_response()
            if last_resp:
                system += (
                    "\n\nIMPORTANT: Your previous response was:\n"
                    + repr(last_resp[:120])
                    + "\nDo NOT repeat yourself. Give a DIFFERENT, contextually appropriate response."
                )
            response = self.gemini.generate(system, user_prompt, history=history)
            if last_resp and response.strip() == last_resp.strip():
                _dbg("WARN", "handle_prompt", "Response identical to last — regenerating")
                system += "\n\nYour response was a duplicate. Generate a completely different reply now."
                response = self.gemini.generate(system, user_prompt, history=history)
            log = ["  No DB changes (conversational)."]
            self._save(InteractionRecord(
                timestamp=datetime.utcnow().isoformat(),
                user_prompt=user_prompt, atlas_response=response,
                tasks=[], actions_taken=log,
            ))
            step("Done.")
            return response, log

        step("Planning...")
        try:
            plan = self.planner.plan(user_prompt, intent, self._history_context())
        except Exception as e:
            step(f"Planner error: {e}")
            response = self.gemini.generate(load_personality(), user_prompt)
            log = [f"  Planner error – no DB changes: {e}"]
            self._save(InteractionRecord(
                timestamp=datetime.utcnow().isoformat(),
                user_prompt=user_prompt, atlas_response=response,
                tasks=[], actions_taken=log,
            ))
            return response, log

        if not plan.needs_action:
            response = plan.atlas_response or self.gemini.generate(load_personality(), user_prompt)
            log = ["  No DB changes required."]
            self._save(InteractionRecord(
                timestamp=datetime.utcnow().isoformat(),
                user_prompt=user_prompt, atlas_response=response,
                tasks=[], actions_taken=log,
            ))
            step("Done.")
            return response, log

        step("Generating JSON...")
        preview = self._format_plan(plan)
        step("Applying changes...")
        exec_log = self.executor.execute(plan)
        self.db.append_study_log(
            f"{user_prompt[:120]} | intent={intent} | actions={len(plan.actions)}"
        )
        full_log = preview + ["", "─── Execution ───"] + exec_log
        response = plan.atlas_response or self.gemini.generate(load_personality(), user_prompt)
        self._save(InteractionRecord(
            timestamp=datetime.utcnow().isoformat(),
            user_prompt=user_prompt, atlas_response=response,
            tasks=[], actions_taken=exec_log,
        ))
        step("Done.")
        return response, full_log

    def _format_plan(self, plan: ActionPlan) -> List[str]:
        lines = [
            "╔══════════════ ACTION PLAN ══════════════╗",
            f"  Intent    : {plan.intent}",
            f"  Actions   : {len(plan.actions)}",
            f"  Timestamp : {plan.timestamp[:19]}",
        ]
        if plan.reasoning.strip():
            for ln in plan.reasoning.strip().splitlines()[:3]:
                lines.append(f"  Reasoning : {ln.strip()}")
        lines.append("──────────────────────────────────────────")
        for i, a in enumerate(plan.actions, 1):
            lines.append(f"  {i}. [{a.action}] {a.target}")
            p = a.payload
            details = []
            if p.get("title"):        details.append(f"title={str(p['title'])[:40]!r}")
            if p.get("due_date"):     details.append(f"due={p['due_date']}")
            if p.get("priority"):     details.append(f"priority={p['priority']}")
            if p.get("effort_level"): details.append(f"effort={p['effort_level']}")
            if p.get("summary"):      details.append(f"summary={str(p['summary'])[:40]!r}")
            if details:
                lines.append(f"     ↳ {', '.join(details)}")
        lines.append("╚══════════════════════════════════════════╝")
        return lines


# =============================================================================
#  ██  USER CODE SECTION ██
# =============================================================================

def user_custom_command(command: str, agent: AtlasAgent) -> Optional[str]:
    """
    Return a string to display, or None to let Atlas handle normally.
    """
    cmd = command.strip().lower()

    if cmd == "/help":
        return textwrap.dedent("""
            Atlas commands:
              /history   – last 10 session interactions
              /tasks     – all tasks with status
              /summary   – completion summary
              /memory    – daily study history (last 7 days)
              /patterns  – study pattern analysis
              /progress  – progress toward A* in maths
              /help      – this message
              exit       – quit Atlas
        """).strip()

    if cmd == "/history":
        records = agent.load_recent_history(10)
        if not records:
            return "No history yet."
        return "\n".join(
            f"[{r.get('timestamp','')[:16]}] {r.get('user_prompt','')[:80]}"
            for r in records
        )

    if cmd == "/tasks":
        tasks = agent.db.fetch_all_tasks()
        if not tasks:
            return "No tasks yet."
        lines = [f"Tasks ({len(tasks)} total):"]
        for t in tasks[:30]:
            lines.append(f"  [{t['status']}] {t['task_name'] or '(untitled)'} ({t.get('priority','')})")
        return "\n".join(lines)

    if cmd == "/summary":
        try:
            from backend import crud
            from backend.database import SessionLocal
            db = SessionLocal()
            s  = crud.get_summary(db)
            db.close()
            return (
                f"Summary for {s['date']}:\n"
                f"  Total tasks  : {s['total_tasks']}\n"
                f"  Done         : {s['completed']}\n"
                f"  In progress  : {s['in_progress']}\n"
                f"  Not started  : {s['not_started']}\n"
                f"  Completion   : {s['completion_rate_pct']}%\n"
                f"  Overdue      : {s['overdue_count']}\n"
                f"  High-prio open: {s['high_priority_open']}"
            )
        except Exception as e:
            return f"Summary error: {e}"

    if cmd == "/memory":
        days = agent.memory.daily_history(7)
        if not days:
            return "No memory yet – complete some study sessions first."
        lines = ["Daily study memory (last 7 days):"]
        for d in days:
            done   = len(d.completed_tasks)
            missed = len(d.missed_tasks)
            lines.append(f"\n  {d.date}  ✓ {done} done  ✗ {missed} missed")
            if d.completed_tasks:
                lines.append("    Completed: " + ", ".join(d.completed_tasks[:5]))
            if d.missed_tasks:
                lines.append("    Missed:    " + ", ".join(d.missed_tasks[:5]))
            if d.eod_summary:
                lines.append(f"    Summary:   {d.eod_summary[:120]}...")
        return "\n".join(lines)

    if cmd == "/patterns":
        return agent.memory.patterns_summary()

    if cmd == "/progress":
        return agent.memory.progress_toward_a_star()

    # ── ADD YOUR OWN COMMANDS BELOW ──────────────────────────────────────
    return None


# =============================================================================
# END USER CODE SECTION
# =============================================================================

# =============================================================================
# CLI
# =============================================================================

def run_cli(agent: AtlasAgent) -> None:
    print("\n" + "═" * 46)
    print("   Atlas  –  Autonomous AI Study Planner")
    print("═" * 46)
    print("Type any prompt, or /help for commands.\n")

    def status_cb(msg: str) -> None:
        print(f"  ◆ {msg}")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        custom = user_custom_command(user_input, agent)
        if custom is not None:
            print(f"\n{custom}\n" + "─" * 60 + "\n")
            continue

        print()
        try:
            response, log = agent.handle_prompt(user_input, status_cb=status_cb)
        except Exception as e:
            print(f"[Error] {e}")
            continue

        print()
        for line in log:
            print(line)
        print(f"\nAtlas:\n{response}\n" + "─" * 60 + "\n")


# =============================================================================
# GUI  –  Dark obsidian theme, notebook layout
# =============================================================================

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: tk.Tk, config_manager: ConfigManager,
                 agent: AtlasAgent) -> None:
        super().__init__(parent)
        self.title("Atlas Settings")
        self.config_manager = config_manager
        self.agent          = agent
        cfg = config_manager.config
        self.geometry("740x660")
        self.resizable(True, True)
        self.grab_set()
        self.configure(bg=C["bg"])

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # General
        gf = tk.Frame(nb, bg=C["surface"])
        nb.add(gf, text="  General  ")
        fields = [
            ("Gemini API key:", "gemini_entry", cfg.gemini_api_key,  60, True),
            ("Model name:",     "model_entry",  cfg.model_name,      40, False),
            ("Notion token:",   "notion_entry", cfg.notion_token,    60, True),
        ]
        for row, (label, attr, value, width, secret) in enumerate(fields):
            tk.Label(gf, text=label, bg=C["surface"], fg=C["muted"],
                     font=("Helvetica", 11)).grid(row=row, column=0, sticky="w", padx=12, pady=10)
            e = tk.Entry(gf, width=width, show="•" if secret else "",
                         bg=C["surface2"], fg=C["text"], insertbackground=C["text"],
                         relief=tk.FLAT, font=("Helvetica", 11))
            e.insert(0, value)
            e.grid(row=row, column=1, sticky="ew", padx=12, pady=10)
            setattr(self, attr, e)
        gf.columnconfigure(1, weight=1)

        # Data source selector
        ds_row = len(fields)
        tk.Label(gf, text="Data source:", bg=C["surface"], fg=C["muted"],
                 font=("Helvetica", 11)).grid(row=ds_row, column=0, sticky="w", padx=12, pady=10)
        self.data_source_var = tk.StringVar(value=cfg.data_source or "local")
        ds_select = ttk.Combobox(gf, textvariable=self.data_source_var,
                                 values=["local", "notion"], state="readonly", width=18)
        ds_select.grid(row=ds_row, column=1, sticky="w", padx=12, pady=10)

        # Personality
        pf = tk.Frame(nb, bg=C["surface"])
        nb.add(pf, text="  Personality  ")
        tk.Label(pf, text="Atlas personality:", bg=C["surface"],
                 fg=C["muted"], font=("Helvetica", 11)).pack(anchor="w", padx=12, pady=(10, 4))
        self.personality_text = tk.Text(pf, wrap=tk.WORD, height=18,
                                        bg=C["surface2"], fg=C["text"],
                                        insertbackground=C["text"],
                                        relief=tk.FLAT, font=("Helvetica", 11),
                                        padx=8, pady=8)
        self.personality_text.insert(tk.END, load_personality())
        self.personality_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Notion spaces
        nf = tk.Frame(nb, bg=C["surface"])
        nb.add(nf, text="  Notion Spaces  ")
        left  = tk.LabelFrame(nf, text="Spaces", bg=C["surface"],
                              fg=C["muted"], font=("Helvetica", 10))
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 6), pady=12)
        right = tk.LabelFrame(nf, text="Details", bg=C["surface"],
                              fg=C["muted"], font=("Helvetica", 10))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12), pady=12)

        self.space_listbox = tk.Listbox(left, height=10, width=22,
                                        bg=C["surface2"], fg=C["text"],
                                        selectbackground=C["accent"],
                                        relief=tk.FLAT, font=("Helvetica", 11))
        self.space_listbox.pack(fill=tk.Y, padx=4, pady=4)
        for s in cfg.study_lists:
            self.space_listbox.insert(tk.END, s.name)
        self.space_listbox.select_set(
            max(0, min(cfg.active_study_list_index, len(cfg.study_lists) - 1))
        )
        br = tk.Frame(left, bg=C["surface"])
        br.pack(fill=tk.X, pady=(4, 8))
        for txt, cmd in [("Add", self._add_space), ("Remove", self._remove_space)]:
            tk.Button(br, text=txt, command=cmd, bg=C["surface2"], fg=C["text"],
                      relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)

        self.space_name_var = tk.StringVar()
        self.space_db_var   = tk.StringVar()
        self.space_log_var  = tk.StringVar()
        for row, (lbl, var) in enumerate([
            ("Space name:",        self.space_name_var),
            ("Database ID:",       self.space_db_var),
            ("Study Log page ID:", self.space_log_var),
        ]):
            tk.Label(right, text=lbl, bg=C["surface"], fg=C["muted"],
                     font=("Helvetica", 11)).grid(row=row, column=0, sticky="w", padx=8, pady=8)
            tk.Entry(right, textvariable=var, width=42,
                     bg=C["surface2"], fg=C["text"], insertbackground=C["text"],
                     relief=tk.FLAT, font=("Helvetica", 11)).grid(
                row=row, column=1, sticky="ew", padx=8, pady=8
            )
        right.columnconfigure(1, weight=1)
        self.space_listbox.bind("<<ListboxSelect>>", lambda _: self._load_space())
        self._load_space()

        # Save button
        bot = tk.Frame(self, bg=C["bg"])
        bot.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=10)
        tk.Button(bot, text="Save & Apply", command=self._on_save,
                  bg=C["accent"], fg="white", relief=tk.FLAT,
                  font=("Helvetica", 12, "bold"), padx=16, pady=6).pack(side=tk.RIGHT)
        tk.Button(bot, text="Close", command=self.destroy,
                  bg=C["surface2"], fg=C["text"], relief=tk.FLAT,
                  padx=12, pady=6).pack(side=tk.RIGHT, padx=8)

    def _sel_idx(self) -> int:
        sel = self.space_listbox.curselection()
        return int(sel[0]) if sel else 0

    def _load_space(self) -> None:
        cfg = self.config_manager.config
        idx = max(0, min(self._sel_idx(), len(cfg.study_lists) - 1))
        s   = cfg.study_lists[idx]
        self.space_name_var.set(s.name)
        self.space_db_var.set(s.database_id)
        self.space_log_var.set(s.study_log_page_id)

    def _add_space(self) -> None:
        cfg = self.config_manager.config
        cfg.study_lists.append(StudyListConfig(name="New Space"))
        self.space_listbox.insert(tk.END, "New Space")
        self.space_listbox.select_clear(0, tk.END)
        self.space_listbox.select_set(tk.END)
        self._load_space()

    def _remove_space(self) -> None:
        cfg = self.config_manager.config
        if len(cfg.study_lists) <= 1:
            return
        idx = self._sel_idx()
        del cfg.study_lists[idx]
        self.space_listbox.delete(idx)
        self.space_listbox.select_set(0)
        cfg.active_study_list_index = 0
        self._load_space()

    def _on_save(self) -> None:
        cfg = self.config_manager.config
        cfg.gemini_api_key = self.gemini_entry.get().strip()
        cfg.model_name     = self.model_entry.get().strip() or "gemini-1.5-flash"
        cfg.notion_token   = self.notion_entry.get().strip()
        ds = (self.data_source_var.get() or "local").lower()
        if ds not in {"local", "notion"}:
            ds = "local"
        cfg.data_source    = ds
        new_p = self.personality_text.get("1.0", tk.END).strip() or DEFAULT_PERSONALITY
        cfg.personality    = new_p
        save_personality(new_p)

        idx = max(0, min(self._sel_idx(), len(cfg.study_lists) - 1))
        s   = cfg.study_lists[idx]
        s.name                    = self.space_name_var.get().strip() or s.name
        s.database_id             = self.space_db_var.get().strip()
        s.study_log_page_id       = self.space_log_var.get().strip()
        cfg.active_study_list_index = idx
        self.space_listbox.delete(idx)
        self.space_listbox.insert(idx, s.name)
        self.space_listbox.select_clear(0, tk.END)
        self.space_listbox.select_set(idx)
        self.config_manager.save(cfg)

        try:
            new_gemini = GeminiClient(cfg.gemini_api_key, cfg.model_name)
        except Exception as e:
            messagebox.showerror("Atlas", f"Gemini error: {e}")
            return

        active = cfg.study_lists[cfg.active_study_list_index]
        local_db = LocalTaskDB()
        notion = NotionClient(cfg.notion_token, active.database_id, active.study_log_page_id, logger=_dbg)
        service = TaskService(cfg.data_source, notion, local_db, logger=_dbg)
        self.agent.config   = cfg
        self.agent.gemini   = new_gemini
        self.agent.db       = service
        self.agent.notion   = service
        self.agent.planner  = ActionPlanner(new_gemini, service, self.agent.memory)
        self.agent.executor = ActionExecutor(service)
        self.agent.eod      = EndOfDayHandler(new_gemini, service, self.agent.memory)
        messagebox.showinfo("Atlas", "Settings saved and applied.")


class AtlasGUI:
    """
    Dark obsidian GUI.
    Layout:
      Top bar  ─ title + settings button
      Prompt   ─ always-visible input box
      Notebook ─ Chat | Action Log | Memory | Progress tabs
      Status   ─ animated step indicator
      Buttons  ─ Send / Clear / Exit
    """

    # Step labels for transparent reasoning
    STEPS = ["Thinking...", "Planning...", "Generating JSON...", "Applying changes...", "Done."]

    def __init__(self, root: tk.Tk, agent: AtlasAgent,
                 config_manager: ConfigManager) -> None:
        self.root           = root
        self.agent          = agent
        self.config_manager = config_manager
        self._thinking      = False

        root.title("Atlas")
        root.geometry("960x720")
        root.minsize(640, 480)
        root.configure(bg=C["bg"])

        # ── Status bar (BOTTOM first) ──────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Frame(root, bg=C["surface"], height=28)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        self._step_dot = tk.Label(status_bar, text="●", bg=C["surface"],
                                   fg=C["green"], font=("Helvetica", 10))
        self._step_dot.pack(side=tk.LEFT, padx=(10, 4))
        tk.Label(status_bar, textvariable=self.status_var, bg=C["surface"],
                 fg=C["muted"], font=("Helvetica", 10), anchor="w").pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        # ── Button bar (BOTTOM second) ─────────────────────────────────────
        bot = tk.Frame(root, bg=C["bg"])
        bot.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=8)

        self.send_btn = tk.Button(
            bot, text="Send  ↵", command=self._on_send,
            bg=C["accent"], fg="white", activebackground=C["accent2"],
            relief=tk.FLAT, font=("Helvetica", 12, "bold"),
            padx=20, pady=7, cursor="hand2",
        )
        self.send_btn.pack(side=tk.LEFT)

        tk.Button(
            bot, text="Clear", command=self._on_clear,
            bg=C["surface2"], fg=C["muted"], relief=tk.FLAT,
            font=("Helvetica", 11), padx=14, pady=7, cursor="hand2",
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            bot, text="Exit", command=root.quit,
            bg=C["surface2"], fg=C["red"], relief=tk.FLAT,
            font=("Helvetica", 11), padx=14, pady=7, cursor="hand2",
        ).pack(side=tk.RIGHT)

        # ── Top bar ────────────────────────────────────────────────────────
        top = tk.Frame(root, bg=C["surface"], height=52)
        top.pack(side=tk.TOP, fill=tk.X)
        top.pack_propagate(False)

        tk.Label(
            top, text="  ◈  ATLAS", bg=C["surface"], fg=C["heading"],
            font=("Courier", 16, "bold"),
        ).pack(side=tk.LEFT, padx=14)

        tk.Label(
            top, text="Autonomous AI Study Planner", bg=C["surface"],
            fg=C["muted"], font=("Helvetica", 10),
        ).pack(side=tk.LEFT, padx=(0, 20))

        tk.Button(
            top, text="⚙  Settings", command=self._open_settings,
            bg=C["surface"], fg=C["muted"], relief=tk.FLAT,
            font=("Helvetica", 10), padx=10, pady=4, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=12)

        # ── Prompt box ────────────────────────────────────────────────────
        prompt_outer = tk.Frame(root, bg=C["border"], pady=1)
        prompt_outer.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(10, 0))
        prompt_inner = tk.Frame(prompt_outer, bg=C["surface2"])
        prompt_inner.pack(fill=tk.X)

        self.prompt_box = tk.Text(
            prompt_inner, height=3, wrap=tk.WORD,
            bg=C["surface2"], fg=C["text"], insertbackground=C["accent"],
            relief=tk.FLAT, font=("Helvetica", 12),
            padx=12, pady=10,
        )
        self.prompt_box.pack(fill=tk.X)
        self.prompt_box.bind("<Return>",       self._on_enter_key)
        self.prompt_box.bind("<Shift-Return>", lambda e: None)  # allow newline
        self._set_placeholder()

        # ── Notebook ──────────────────────────────────────────────────────
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Atlas.TNotebook",
                         background=C["bg"], borderwidth=0, tabmargins=0)
        style.configure("Atlas.TNotebook.Tab",
                         background=C["surface"], foreground=C["muted"],
                         padding=[16, 6], font=("Helvetica", 10),
                         borderwidth=0)
        style.map("Atlas.TNotebook.Tab",
                  background=[("selected", C["surface2"])],
                  foreground=[("selected", C["heading"])])

        nb = ttk.Notebook(root, style="Atlas.TNotebook")
        nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=10)
        self._nb = nb

        # Tab 1 – Chat
        chat_tab = tk.Frame(nb, bg=C["surface"])
        nb.add(chat_tab, text="  Chat  ")
        self.response_box = tk.Text(
            chat_tab, wrap=tk.WORD, state=tk.DISABLED,
            bg=C["surface"], fg=C["text"], relief=tk.FLAT,
            font=("Helvetica", 12), padx=16, pady=12,
            spacing1=4, spacing3=4,
        )
        chat_scroll = tk.Scrollbar(chat_tab, command=self.response_box.yview,
                                   bg=C["surface2"], troughcolor=C["surface"],
                                   relief=tk.FLAT)
        self.response_box.configure(yscrollcommand=chat_scroll.set)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.response_box.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for styled chat output
        self.response_box.tag_configure("you",
            foreground=C["accent"], font=("Helvetica", 12, "bold"))
        self.response_box.tag_configure("atlas",
            foreground=C["green"], font=("Helvetica", 12, "bold"))
        self.response_box.tag_configure("body",
            foreground=C["text"], font=("Helvetica", 12))
        self.response_box.tag_configure("divider",
            foreground=C["border"])

        # Tab 2 – Action Log
        log_tab = tk.Frame(nb, bg=C["surface"])
        nb.add(log_tab, text="  Action Log  ")
        self.log_box = tk.Text(
            log_tab, wrap=tk.WORD, state=tk.DISABLED,
            bg=C["surface"], fg=C["muted"], relief=tk.FLAT,
            font=("Courier", 10), padx=16, pady=12,
        )
        log_scroll = tk.Scrollbar(log_tab, command=self.log_box.yview,
                                  bg=C["surface2"], troughcolor=C["surface"],
                                  relief=tk.FLAT)
        self.log_box.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        self.log_box.tag_configure("ok",     foreground=C["green"])
        self.log_box.tag_configure("fail",   foreground=C["red"])
        self.log_box.tag_configure("header", foreground=C["accent"],
                                   font=("Courier", 10, "bold"))

        # Tab 3 – Memory
        mem_tab = tk.Frame(nb, bg=C["surface"])
        nb.add(mem_tab, text="  Memory  ")

        mem_btn_bar = tk.Frame(mem_tab, bg=C["surface"])
        mem_btn_bar.pack(fill=tk.X, padx=8, pady=6)
        for label, cmd_str in [
            ("Daily History", "/memory"),
            ("Patterns",      "/patterns"),
            ("A* Progress",   "/progress"),
        ]:
            tk.Button(
                mem_btn_bar, text=label,
                command=lambda c=cmd_str: self._run_memory_command(c),
                bg=C["surface2"], fg=C["text"], relief=tk.FLAT,
                font=("Helvetica", 10), padx=12, pady=5, cursor="hand2",
            ).pack(side=tk.LEFT, padx=(0, 6))

        self.memory_box = tk.Text(
            mem_tab, wrap=tk.WORD, state=tk.DISABLED,
            bg=C["surface"], fg=C["text"], relief=tk.FLAT,
            font=("Courier", 11), padx=16, pady=12,
        )
        mem_scroll = tk.Scrollbar(mem_tab, command=self.memory_box.yview,
                                  bg=C["surface2"], troughcolor=C["surface"],
                                  relief=tk.FLAT)
        self.memory_box.configure(yscrollcommand=mem_scroll.set)
        mem_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.memory_box.pack(fill=tk.BOTH, expand=True)

        # Tab 4 – Tasks
        tasks_tab = tk.Frame(nb, bg=C["surface"])
        nb.add(tasks_tab, text="  Tasks  ")

        tasks_btn_bar = tk.Frame(tasks_tab, bg=C["surface"])
        tasks_btn_bar.pack(fill=tk.X, padx=8, pady=6)
        tk.Button(
            tasks_btn_bar, text="↺ Refresh",
            command=lambda: self._run_memory_command("/tasks"),
            bg=C["accent"], fg="white", relief=tk.FLAT,
            font=("Helvetica", 10), padx=12, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT)

        self.tasks_box = tk.Text(
            tasks_tab, wrap=tk.WORD, state=tk.DISABLED,
            bg=C["surface"], fg=C["text"], relief=tk.FLAT,
            font=("Courier", 11), padx=16, pady=12,
        )
        tasks_scroll = tk.Scrollbar(tasks_tab, command=self.tasks_box.yview,
                                    bg=C["surface2"], troughcolor=C["surface"],
                                    relief=tk.FLAT)
        self.tasks_box.configure(yscrollcommand=tasks_scroll.set)
        tasks_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tasks_box.pack(fill=tk.BOTH, expand=True)

    # ── Placeholder ───────────────────────────────────────────────────────

    def _set_placeholder(self) -> None:
        self.prompt_box.insert("1.0", "Ask Atlas anything or give a study goal...")
        self.prompt_box.configure(fg=C["muted"])
        self.prompt_box.bind("<FocusIn>",  self._clear_placeholder)
        self.prompt_box.bind("<FocusOut>", self._restore_placeholder)
        self._has_placeholder = True

    def _clear_placeholder(self, _event=None) -> None:
        if getattr(self, "_has_placeholder", False):
            self.prompt_box.delete("1.0", tk.END)
            self.prompt_box.configure(fg=C["text"])
            self._has_placeholder = False

    def _restore_placeholder(self, _event=None) -> None:
        if not self.prompt_box.get("1.0", tk.END).strip():
            self.prompt_box.delete("1.0", tk.END)
            self.prompt_box.insert("1.0", "Ask Atlas anything or give a study goal...")
            self.prompt_box.configure(fg=C["muted"])
            self._has_placeholder = True

    # ── Chat helpers ──────────────────────────────────────────────────────

    def _chat_append(self, speaker: str, text: str) -> None:
        box = self.response_box
        box.configure(state=tk.NORMAL)
        tag = "you" if speaker == "You" else "atlas"
        box.insert(tk.END, f"{speaker}\n", tag)
        box.insert(tk.END, text + "\n", "body")
        box.insert(tk.END, "─" * 56 + "\n\n", "divider")
        box.see(tk.END)
        box.configure(state=tk.DISABLED)

    def _log_append(self, lines: List[str]) -> None:
        box = self.log_box
        box.configure(state=tk.NORMAL)
        for line in lines:
            tag = "ok" if "✓" in line or "OK" in line else \
                  "fail" if "✗" in line or "ERR" in line or "FAIL" in line else \
                  "header" if line.startswith("╔") or line.startswith("╚") or \
                               line.startswith("──") else ""
            box.insert(tk.END, line + "\n", tag)
        box.insert(tk.END, "\n")
        box.see(tk.END)
        box.configure(state=tk.DISABLED)

    def _memory_write(self, text: str) -> None:
        self.memory_box.configure(state=tk.NORMAL)
        self.memory_box.delete("1.0", tk.END)
        self.memory_box.insert(tk.END, text)
        self.memory_box.configure(state=tk.DISABLED)

    def _tasks_write(self, text: str) -> None:
        self.tasks_box.configure(state=tk.NORMAL)
        self.tasks_box.delete("1.0", tk.END)
        self.tasks_box.insert(tk.END, text)
        self.tasks_box.configure(state=tk.DISABLED)

    # ── Status / step indicator ───────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)
        color = C["orange"] if msg not in ("Ready", "Done.") else C["green"]
        self._step_dot.configure(fg=color)
        self.root.update_idletasks()

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_enter_key(self, event) -> str:
        if not event.state & 0x1:  # Shift not held
            self._on_send()
            return "break"
        return None

    def _on_send(self) -> None:
        if getattr(self, "_has_placeholder", False):
            return
        user_prompt = self.prompt_box.get("1.0", tk.END).strip()
        if not user_prompt:
            return

        self._chat_append("You", user_prompt)
        self.prompt_box.delete("1.0", tk.END)
        self._has_placeholder = False
        self.send_btn.configure(state=tk.DISABLED, bg=C["border"])
        self._set_status("Thinking...")
        self._nb.select(0)

        def _run() -> None:
            try:
                custom = user_custom_command(user_prompt, self.agent)
                if custom is not None:
                    response, log = custom, ["  Custom command."]
                else:
                    response, log = self.agent.handle_prompt(
                        user_prompt,
                        status_cb=lambda m: self.root.after(0, lambda msg=m: self._set_status(msg))
                    )
            except Exception as e:
                response = f"Error: {e}"
                log      = [f"ERROR: {e}"]
            self.root.after(0, lambda: self._on_done(response, log))

        threading.Thread(target=_run, daemon=True).start()

    def _on_done(self, response: str, log: List[str]) -> None:
        self._chat_append("Atlas", response)
        self._log_append(log)
        self.send_btn.configure(state=tk.NORMAL, bg=C["accent"])
        self._set_status("Ready")

    def _on_clear(self) -> None:
        for box in (self.response_box, self.log_box):
            box.configure(state=tk.NORMAL)
            box.delete("1.0", tk.END)
            box.configure(state=tk.DISABLED)

    def _run_memory_command(self, cmd: str) -> None:
        result = user_custom_command(cmd, self.agent)
        if result is None:
            result = "(no data)"
        if cmd == "/tasks":
            self._tasks_write(result)
            # Switch to Tasks tab
            for i in range(self._nb.index("end")):
                if "Task" in self._nb.tab(i, "text"):
                    self._nb.select(i)
                    break
        else:
            self._memory_write(result)
            # Switch to Memory tab
            for i in range(self._nb.index("end")):
                if "Memory" in self._nb.tab(i, "text"):
                    self._nb.select(i)
                    break

    def _open_settings(self) -> None:
        SettingsWindow(self.root, self.config_manager, self.agent)


def run_gui(agent: AtlasAgent, config_manager: ConfigManager) -> None:
    if not TK_AVAILABLE:
        print("Tkinter not available. Use: python agent.py --cli")
        return
    root = tk.Tk()
    AtlasGUI(root, agent, config_manager)
    root.mainloop()


# =============================================================================
# BOOTSTRAP
# =============================================================================

def build_agent(config_manager: ConfigManager) -> AtlasAgent:
    cfg    = config_manager.config
    gemini = GeminiClient(cfg.gemini_api_key, cfg.model_name)
    if not cfg.study_lists:
        cfg.study_lists.append(StudyListConfig())
    idx   = max(0, min(cfg.active_study_list_index, len(cfg.study_lists) - 1))
    space = cfg.study_lists[idx]
    local_db = LocalTaskDB()
    notion = NotionClient(cfg.notion_token, space.database_id, space.study_log_page_id, logger=_dbg)
    service = TaskService(cfg.data_source, notion, local_db, logger=_dbg)
    return AtlasAgent(config=cfg, gemini=gemini, db=service)


def main() -> None:
    config_manager = ConfigManager()
    try:
        agent = build_agent(config_manager)
    except Exception as e:
        print(f"[Startup] Failed: {e}")
        sys.exit(1)

    mode = "--gui" if TK_AVAILABLE else "--cli"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode in {"--gui", "gui"}:
        run_gui(agent, config_manager)
    else:
        run_cli(agent)


if __name__ == "__main__":
    main()
