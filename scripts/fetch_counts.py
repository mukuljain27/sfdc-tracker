#!/usr/bin/env python3
"""
SFDC Jira Tracker — data fetcher
Runs via GitHub Actions at 9 AM and 6:30 PM IST.
Fetches all open SFDC issues from Jira, computes module-wise counts,
then injects the updated data into index.html between the ACTION_DATA markers.

Required environment variables:
  JIRA_EMAIL  — your Atlassian account email
  JIRA_TOKEN  — your Atlassian API token (from id.atlassian.com/manage-profile/security)
"""

import os, sys, json, re, requests
from datetime import datetime, timezone, timedelta
from base64 import b64encode

# ── Config ────────────────────────────────────────────────────
JIRA_BASE   = "https://birdeye.atlassian.net"
JIRA_EMAIL  = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN  = os.environ.get("JIRA_TOKEN", "")
IST         = timezone(timedelta(hours=5, minutes=30))
BASE_JQL    = (
    'project = BIRDEYE '
    'AND status not in (Closed, "Live on Production", "Verified on Production", '
    '"With Support", Done, BLOCKED, LAUNCHED, "LAUNCH VERIFIED", Resolved) '
    'AND salesforceAssociatedIds is not EMPTY '
    'AND "SFDC Case Type[Dropdown]" not in ("Feature Request") '
    'AND "SFDC Case Category[Dropdown]" not in ("Business Systems") '
    'AND ("SFDC Module[Dropdown]" not in ("Business Systems") '
    'OR "SFDC Module New[Short text]" !~ "Business Systems")'
)

def auth_header():
    creds = b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Accept": "application/json"}

def fetch_all_issues():
    issues, start = [], 0
    while True:
        resp = requests.get(
            f"{JIRA_BASE}/rest/api/3/search",
            headers=auth_header(),
            params={
                "jql": BASE_JQL + " ORDER BY createdDate DESC",
                "fields": "customfield_11027,status,assignee",
                "maxResults": 100,
                "startAt": start
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("issues", [])
        issues.extend(batch)
        start += len(batch)
        print(f"  Fetched {start} / {data.get('total', '?')} issues…")
        if start >= data.get("total", 0) or not batch:
            break
    return issues

def compute_modules(issues):
    modules = {}
    for iss in issues:
        cf = (iss.get("fields") or {}).get("customfield_11027")
        if cf and isinstance(cf.get("value"), str):
            mod = cf["value"]
            modules[mod] = modules.get(mod, 0) + 1
    return modules

def load_html():
    path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    with open(path, "r") as f:
        return f.read(), path

def inject_data(html, new_data):
    new_block = "const TRACKER_DATA = " + json.dumps(new_data, indent=2, ensure_ascii=False) + ";"
    # Replace between ACTION_DATA_START and ACTION_DATA_END markers
    pattern = r'(// ACTION_DATA_START\n).*?(\n// ACTION_DATA_END)'
    replacement = r'\g<1>' + new_block + r'\2'
    updated = re.sub(pattern, replacement, html, flags=re.DOTALL)
    if updated == html:
        print("WARNING: Could not find ACTION_DATA markers in index.html")
    return updated

def main():
    now_ist = datetime.now(IST)
    today   = now_ist.strftime("%Y-%m-%d")
    h, m    = now_ist.hour, now_ist.minute
    time_str = now_ist.strftime("%I:%M %p")

    # Determine capture window
    is_morning = (h == 9)
    is_evening = (h == 18 and m >= 30) or (h == 19 and m < 30)
    window     = "morning" if is_morning else ("evening" if is_evening else "current")

    print(f"SFDC Tracker fetch — {now_ist.strftime('%Y-%m-%d %H:%M IST')} — window: {window}")

    if not JIRA_EMAIL or not JIRA_TOKEN:
        print("ERROR: JIRA_EMAIL and JIRA_TOKEN must be set as environment variables")
        sys.exit(1)

    print("Fetching issues from Jira…")
    issues  = fetch_all_issues()
    modules = compute_modules(issues)
    total   = len(issues)
    print(f"Total: {total} issues across {len(modules)} modules")

    # Load existing data from index.html
    html, path = load_html()
    match = re.search(r'// ACTION_DATA_START\nconst TRACKER_DATA = (.+?);\n// ACTION_DATA_END', html, re.DOTALL)
    existing = {}
    if match:
        try:
            existing = json.loads(match.group(1))
        except Exception as e:
            print(f"WARNING: Could not parse existing data: {e}")

    # Preserve or reset today's data
    if existing.get("date") != today:
        # New day — reset
        existing = {"date": today, "lastUpdated": "", "morning": None, "evening": None, "history": existing.get("history", [])}

    snap = {"time": time_str, "total": total, "modules": modules}

    if window == "morning" and not existing.get("morning"):
        existing["morning"] = snap
        print(f"✓ Saved as MORNING count: {total} issues")
    elif window == "evening" and not existing.get("evening"):
        existing["evening"] = snap
        print(f"✓ Saved as EVENING count: {total} issues")
    else:
        # Outside capture window — update current but don't overwrite morning/evening
        existing["current"] = snap
        print(f"✓ Saved as CURRENT count: {total} issues (outside capture window)")

    existing["lastUpdated"] = now_ist.isoformat()

    # Append to history if we have a morning and/or evening for today
    history = existing.get("history", [])
    today_hist = next((d for d in history if d.get("date") == today), None)
    if today_hist is None:
        today_hist = {"date": today}
        history.append(today_hist)
    if existing.get("morning"):
        today_hist["morning"] = {"time": existing["morning"]["time"], "total": existing["morning"]["total"]}
    if existing.get("evening"):
        today_hist["evening"] = {"time": existing["evening"]["time"], "total": existing["evening"]["total"]}
    # Keep last 7 days
    existing["history"] = sorted(history, key=lambda d: d["date"])[-7:]

    # Write updated HTML
    updated_html = inject_data(html, existing)
    with open(path, "w") as f:
        f.write(updated_html)
    print(f"✓ index.html updated successfully")

if __name__ == "__main__":
    main()
