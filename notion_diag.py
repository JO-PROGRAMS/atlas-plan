#!/usr/bin/env python3
"""
Notion Diagnostic — run this in your Atlas folder:
  python3 notion_diag.py
"""
import json, sys, os
import requests

# ── Load config ──────────────────────────────────────────────────────────
cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
try:
    cfg = json.load(open(cfg_path))
except Exception as e:
    print(f"✗ Cannot read config.json: {e}")
    sys.exit(1)

token     = cfg.get("notion_token", "")
sl        = (cfg.get("study_lists") or [{}])[ cfg.get("active_study_list_index", 0) ]
db_id     = sl.get("database_id", "").replace("-","")
log_id    = sl.get("study_log_page_id", "").replace("-","")

print(f"token      : {token[:12]}... ({len(token)} chars)")
print(f"database_id: '{db_id}' ({len(db_id)} chars)")
print(f"log_page_id: '{log_id}' ({len(log_id)} chars)")
print()

headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

BASE = "https://api.notion.com/v1"

# ── Test 1: fetch DB ──────────────────────────────────────────────────────
print("── Test 1: GET database ──────────────────────")
r = requests.get(f"{BASE}/databases/{db_id}", headers=headers, timeout=10)
print(f"Status: {r.status_code}")
if r.ok:
    d = r.json()
    title = (d.get("title") or [{}])[0].get("plain_text","?")
    props = list(d.get("properties",{}).keys())
    print(f"✓ DB title: '{title}'")
    print(f"✓ Columns: {props}")
else:
    print(f"✗ Error: {r.text[:400]}")
    sys.exit(1)

# ── Test 2: query DB ──────────────────────────────────────────────────────
print("\n── Test 2: Query DB ──────────────────────────")
r2 = requests.post(f"{BASE}/databases/{db_id}/query", headers=headers, json={"page_size":3}, timeout=10)
print(f"Status: {r2.status_code}")
if r2.ok:
    pages = r2.json().get("results",[])
    print(f"✓ Rows returned: {len(pages)}")
    for p in pages[:2]:
        props = p.get("properties",{})
        title_items = props.get("Task name",{}).get("title",[])
        title_text = title_items[0].get("plain_text","?") if title_items else "?"
        print(f"  - '{title_text}'")
else:
    print(f"✗ Error: {r2.text[:400]}")

# ── Test 3: create a test task ────────────────────────────────────────────
print("\n── Test 3: CREATE a test page ────────────────")
payload = {
    "parent": {"database_id": db_id},
    "properties": {
        "Task name": {"title": [{"text": {"content": "🧪 DIAGNOSTIC TEST TASK — delete me"}}]},
        "Status": {"status": {"name": "Not started"}},
        "Priority": {"select": {"name": "Low"}},
    }
}
print(f"Payload: {json.dumps(payload, indent=2)}")
r3 = requests.post(f"{BASE}/pages", headers=headers, json=payload, timeout=15)
print(f"Status: {r3.status_code}")
if r3.ok:
    new_id = r3.json().get("id","?")
    print(f"✓ Created page id: {new_id}")
    # Clean up — archive it
    r4 = requests.patch(f"{BASE}/pages/{new_id}", headers=headers, json={"archived": True}, timeout=10)
    print(f"✓ Archived (cleaned up): {r4.status_code}")
else:
    print(f"✗ CREATE FAILED!")
    resp = r3.json()
    print(f"  code   : {resp.get('code')}")
    print(f"  message: {resp.get('message')}")
    print(f"  full   : {r3.text[:600]}")

print("\nDone. Share the output above to diagnose the issue.")
