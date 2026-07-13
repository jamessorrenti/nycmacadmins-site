#!/usr/bin/env python3
"""Pulls the NYC Mac Admins events Google Sheet (published "anyone with the
link" CSV export) and writes data/events.json for Hugo to build from.

Run by .github/workflows/events-sync.yaml on a schedule and on demand; no
Apps Script or credentials involved — the sheet's CSV export endpoint is
public, so this is a plain HTTP GET + parse.

The sheet isn't hardcoded here: set the EVENTS_SHEET_URL environment
variable to the sheet's share/edit link (or its ID, or a direct CSV export
URL — any of those work) — in CI this comes from the repo variable
EVENTS_SHEET_URL (Settings → Secrets and variables → Actions → Variables),
not a secret, since the sheet itself is public.

Sheet columns (header row, order doesn't matter):
  slug | status | title | date | start | doors | location_name | address |
  general_info | presentation_title | presentation_info | speakers |
  sponsor | sponsor_info | sponsor_link | signup_link | contact_email

  date            M/D/YYYY                  (e.g. 7/21/2026)
  start / doors   bare time-of-day           (e.g. "4:30 PM"); doors optional
  status          published | draft | canceled — draft rows are dropped
  speakers        comma-separated

`date` + `start` / `date` + `doors` are combined into ISO 8601 datetimes
with the correct America/New_York UTC offset (DST-aware).
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_JSON_PATH = REPO_ROOT / "data" / "events.json"
TZ = ZoneInfo("America/New_York")

_SHEET_ID_RE = re.compile(r"/d/([a-zA-Z0-9-_]+)")
_GID_RE = re.compile(r"[?&#]gid=(\d+)")


def sheet_csv_url() -> str:
    """Build the CSV export URL from EVENTS_SHEET_URL, which may be a share/
    edit link, a bare sheet ID, or an already-direct CSV export URL."""
    raw = os.environ.get("EVENTS_SHEET_URL", "").strip()
    if not raw:
        raise SystemExit(
            "EVENTS_SHEET_URL is not set. Set it to the sheet's share link "
            "(Settings → Secrets and variables → Actions → Variables in "
            "CI, or export it locally before running this script)."
        )

    id_match = _SHEET_ID_RE.search(raw)
    sheet_id = id_match.group(1) if id_match else raw
    gid_match = _GID_RE.search(raw)
    gid = gid_match.group(1) if gid_match else "0"

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_csv(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "nycmacadmins-site/sync_events"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8-sig")


def parse_time_of_day(s: str) -> tuple[int, int]:
    """'4:30 PM' / '16:30' / '4:30:00 PM' -> (hour, minute), 24h."""
    s = s.strip()
    for fmt in ("%I:%M %p", "%I:%M:%S %p", "%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(s, fmt)
            return t.hour, t.minute
        except ValueError:
            continue
    raise ValueError(f"Unparseable time: {s!r}")


def parse_date(s: str) -> tuple[int, int, int]:
    """'7/21/2026' / '2026-07-21' -> (year, month, day)."""
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.year, d.month, d.day
        except ValueError:
            continue
    raise ValueError(f"Unparseable date: {s!r}")


def combine_iso(date_str: str, time_str: str) -> str:
    year, month, day = parse_date(date_str)
    hour, minute = parse_time_of_day(time_str)
    dt = datetime(year, month, day, hour, minute, tzinfo=TZ)
    return dt.isoformat()


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def derive_slug(date_str: str, title: str) -> str:
    year, month, day = parse_date(date_str)
    return f"{year:04d}-{month:02d}-{day:02d}-{slugify(title)}"


def row_get(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def build_event(row: dict) -> dict | None:
    title = row_get(row, "title")
    date_str = row_get(row, "date")
    start_str = row_get(row, "start")
    if not title or not date_str or not start_str:
        print(f"  skip: missing title/date/start -> {row}", file=sys.stderr)
        return None

    status = (row_get(row, "status") or "published").lower()
    if status == "draft":
        return None

    try:
        start_iso = combine_iso(date_str, start_str)
    except ValueError as e:
        print(f"  skip {title!r}: {e}", file=sys.stderr)
        return None

    doors_str = row_get(row, "doors")
    doors_iso = ""
    if doors_str:
        try:
            doors_iso = combine_iso(date_str, doors_str)
        except ValueError as e:
            print(f"  warn {title!r}: doors time unparseable ({e}), omitting", file=sys.stderr)

    slug = row_get(row, "slug") or derive_slug(date_str, title)
    speakers = [s.strip() for s in row_get(row, "speakers").split(",") if s.strip()]

    return {
        "slug": slug,
        "status": status,
        "title": title,
        "start": start_iso,
        "doors": doors_iso,
        "location_name": row_get(row, "location_name"),
        "address": row_get(row, "address"),
        "general_info": row_get(row, "general_info"),
        "presentation_title": row_get(row, "presentation_title"),
        "presentation_info": row_get(row, "presentation_info"),
        "speakers": speakers,
        "sponsor": row_get(row, "sponsor"),
        "sponsor_info": row_get(row, "sponsor_info"),
        "sponsor_link": row_get(row, "sponsor_link"),
        "signup_link": row_get(row, "signup_link"),
        "contact_email": row_get(row, "contact_email"),
    }


def main() -> int:
    url = sheet_csv_url()
    print(f"Fetching {url}")
    text = fetch_csv(url)
    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    events = []
    for row in reader:
        event = build_event(row)
        if event:
            events.append(event)

    events.sort(key=lambda e: e["start"])

    EVENTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_content = json.dumps(events, indent=2) + "\n"
    old_content = EVENTS_JSON_PATH.read_text() if EVENTS_JSON_PATH.exists() else None

    if new_content == old_content:
        print(f"No changes ({len(events)} events, unchanged).")
        return 0

    EVENTS_JSON_PATH.write_text(new_content)
    print(f"Wrote {len(events)} event(s) to {EVENTS_JSON_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
