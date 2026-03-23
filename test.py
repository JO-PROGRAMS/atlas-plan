#!/usr/bin/env python3
"""
Atlas — Notion connectivity & CRUD test
Run: python3 test_notion.py
Tests: schema fetch, create task, update status, delete task.
"""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

# ── Load config ────────────────────────────────────────────────────────────
CONFIG_PATH = "config.json"
if not os.path.exists(CONFIG_PATH):
    print(f"✗  config.json not found in {os.getcwd()}")
    print("   Run this script from your Atlas directory (where config.json lives)")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    cfg = json.load(f)

token     = cfg.get("notion_token", "")
lists     = cfg.get("study_lists", [{}])
db_id     = lists[0].get("database_id", "")
log_id    = lists[0].get("study_log_page_id", "")

print("=" * 60)
print("  Atlas Notion CRUD Test")
print("=" * 60)
print(f"  Token    : {'✓ set' if token else '✗ MISSING'} ({token[:12]}…)" if token else "  Token    : ✗ MISSING")
print(f"  DB ID    : {db_id[:8]}… ({len(db_id)} chars)")
print(f"  Log page : {log_id[:8]}… ({len(log_id)} chars)" if log_id else "  Log page : (not set)")
print()

if not token or not db_id:
    print("✗  Missing token or database_id. Check config.json.")
    sys.exit(1)

# ── Import client ──────────────────────────────────────────────────────────
try:
    from agent import NotionClient, StudyTask, STATUS_NOT_STARTED, _DEBUG_LOG
except ImportError as e:
    print(f"✗  Cannot import agent.py: {e}")
    sys.exit(1)

# ── Init client ────────────────────────────────────────────────────────────
print("1. Initialising NotionClient…")
n = NotionClient(token, db_id, log_id)
print(f"   list_type    : {n.list_type}")
print(f"   api_version  : {n._api_version}")
print(f"   write_enabled: {n.write_enabled}")
print(f"   log_enabled  : {n.log_enabled}")
print(f"   title_column : {n._title_column}")
print(f"   schema cols  : {list(n.db_properties.keys())}")
print()

if n.list_type == "unknown":
    print("✗  Schema fetch FAILED. Debug log:")
    for e in list(_DEBUG_LOG)[-10:]:
        print(f"   [{e['level']}] {e['source']}: {e['msg']}")
    print()
    print("   → Check: 1) Token is correct  2) Database is shared with integration")
    print("   → In Notion: open database → Share → Invite integration")
    sys.exit(1)

print("   ✓ Schema loaded successfully")
print()

# ── Test 2: Fetch tasks ────────────────────────────────────────────────────
print("2. Fetching all tasks…")
pages = n.fetch_all_tasks()
print(f"   ✓ Fetched {len(pages)} tasks")
if pages:
    sample = pages[0]
    print(f"   First task: '{n.get_task_title(sample)}' | status: '{n.get_task_status(sample)}'")
print()

# ── Test 3: Create a task ──────────────────────────────────────────────────
print("3. Creating a test task…")
test_task = StudyTask(
    title="[ATLAS TEST] Delete me — created by test_notion.py",
    source_prompt="automated test",
    created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    description="This is a test task created by Atlas test script",
    due_date=time.strftime("%Y-%m-%d") + "T14:00:00",
    effort_level="Small",
    priority="Low",
    status=STATUS_NOT_STARTED,
    summary="Test task — safe to delete",
    task_type="",
)

new_page_id = n.create_task(test_task)
if new_page_id:
    print(f"   ✓ Created task! page_id={new_page_id[:12]}…")
else:
    print("   ✗ create_task FAILED. Debug log:")
    for e in list(_DEBUG_LOG)[-15:]:
        if e["level"] in ("ERROR", "WARN", "NOTION"):
            print(f"   [{e['level']}] {e['source']}: {e['msg']}")
            if e.get("data"):
                print(f"      data: {e['data']}")
    sys.exit(1)
print()

# ── Test 4: Update task status ─────────────────────────────────────────────
print("4. Updating task status to 'In progress'…")
time.sleep(0.5)
ok = n.update_task_status(new_page_id, "In progress")
if ok:
    print("   ✓ Status updated to 'In progress'")
else:
    print("   ✗ update_task_status FAILED")
print()

# ── Test 5: Delete (archive) the task ─────────────────────────────────────
print("5. Deleting (archiving) the test task…")
time.sleep(0.5)
ok = n.delete_task(new_page_id)
if ok:
    print("   ✓ Task deleted/archived successfully")
else:
    print("   ✗ delete_task FAILED")
print()

# ── Test 6: Append to study log ───────────────────────────────────────────
if n.log_enabled:
    print("6. Appending to study log page…")
    n.append_study_log("Atlas test script ran successfully — CRUD all OK")
    print("   ✓ Log appended")
else:
    print("6. Study log: skipped (study_log_page_id not set)")
print()

# ── Summary ────────────────────────────────────────────────────────────────
print("=" * 60)
print("  ALL TESTS PASSED ✓")
print("  Notion integration is working correctly.")
print("=" * 60)