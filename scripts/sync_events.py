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

## Schema: aligned with macadmins-calendar

Fields that overlap with the community calendar at
https://github.com/macadminsdotorg/macadmins-calendar use ITS exact field
names (name, full_name, start_date, end_date, location, organizer, website,
type, videos, language) — see that repo's README for the spec. That makes
submitting an event there a straight field copy, no renaming. Everything
else below is NYCMA-specific and rides alongside.

Their convention: "name" is a short/common name, "full_name" is longer and
more descriptive (e.g. name: "December 2025 Meetup", full_name: "NYC Mac
Admins December 2025 Meetup"). Our own site and RSS use full_name (falling
back to name) as the displayed title — see content/events/_content.gotmpl —
so short names read fine on macadmins-calendar without looking bare on ours.

Sheet columns (header row, order doesn't matter; case-insensitive):

  Matches macadmins-calendar's field names exactly:
    name            required   short event name, e.g. "December 2025 Meetup"
    full_name       optional   longer/more descriptive name; used as our own page title
    start_date      required   M/D/YYYY or YYYY-MM-DD, e.g. 7/21/2026
    end_date        optional   same formats; defaults to start_date (we're single-day)
    location        optional   "City, State, Country", e.g. "New York, NY, USA"
    organizer       optional   omit when it'd just restate the event name (their convention)
    website         optional   defaults to this event's own page URL if left blank
    type            optional   defaults to "meetup"; we're not only meetups forever
    videos          optional   recording/YouTube link
    language        optional   defaults to "en"; set explicitly to override

  NYCMA-specific (not in their schema):
    slug            optional   URL id; auto-derived from start_date + name if blank
    status          optional   published (default) | draft | canceled
    start_time      required   bare time-of-day, e.g. "4:30 PM" (presentations start)
    doors_time      optional   bare time-of-day, e.g. "4:00 PM" (entry/doors open)
    location_name   optional   venue name, e.g. "Apple, 11 Penn Plaza"
    address         optional   full street address (becomes a map link)
    general_info, presentation_title, presentation_info, speakers (comma-separated),
    sponsor, sponsor_info, sponsor_link, signup_link, contact_email

  Deprecated aliases still read for backward compatibility (prefer the
  names above in new sheets): title -> name, date -> start_date,
  start -> start_time, doors -> doors_time.

`start_date` + `start_time` (and `start_date` + `doors_time`) are combined
into ISO 8601 datetimes with the correct America/New_York UTC offset
(DST-aware) for the site's own use (sorting, display, RSS pubDate).
`start_date`/`end_date` are also kept as plain YYYY-MM-DD strings, matching
macadmins-calendar's format exactly.
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
SITE_URL = "https://nycmacadmins.com"

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


def iso_date(date_str: str) -> str:
    """Normalize any accepted input date to macadmins-calendar's YYYY-MM-DD."""
    year, month, day = parse_date(date_str)
    return f"{year:04d}-{month:02d}-{day:02d}"


def combine_iso(date_str: str, time_str: str) -> str:
    year, month, day = parse_date(date_str)
    hour, minute = parse_time_of_day(time_str)
    dt = datetime(year, month, day, hour, minute, tzinfo=TZ)
    return dt.isoformat()


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def derive_slug(date_str: str, name: str) -> str:
    year, month, day = parse_date(date_str)
    return f"{year:04d}-{month:02d}-{day:02d}-{slugify(name)}"


def row_get(row: dict, *keys: str) -> str:
    """First non-empty value among `keys` (later keys are deprecated aliases)."""
    for key in keys:
        v = (row.get(key) or "").strip()
        if v:
            return v
    return ""


def build_event(row: dict) -> dict | None:
    name = row_get(row, "name", "title")
    start_date_str = row_get(row, "start_date", "date")
    start_time_str = row_get(row, "start_time", "start")
    if not name or not start_date_str or not start_time_str:
        print(f"  skip: missing name/start_date/start_time -> {row}", file=sys.stderr)
        return None

    status = (row_get(row, "status") or "published").lower()
    if status == "draft":
        return None

    try:
        start_iso = combine_iso(start_date_str, start_time_str)
        start_date = iso_date(start_date_str)
    except ValueError as e:
        print(f"  skip {name!r}: {e}", file=sys.stderr)
        return None

    end_date_str = row_get(row, "end_date") or start_date_str
    try:
        end_date = iso_date(end_date_str)
    except ValueError as e:
        print(f"  warn {name!r}: end_date unparseable ({e}), using start_date", file=sys.stderr)
        end_date = start_date

    doors_time_str = row_get(row, "doors_time", "doors")
    doors_iso = ""
    if doors_time_str:
        try:
            doors_iso = combine_iso(start_date_str, doors_time_str)
        except ValueError as e:
            print(f"  warn {name!r}: doors time unparseable ({e}), omitting", file=sys.stderr)

    slug = row_get(row, "slug") or derive_slug(start_date_str, name)
    speakers = [s.strip() for s in row_get(row, "speakers").split(",") if s.strip()]
    website = row_get(row, "website") or f"{SITE_URL}/events/{slug}/"
    event_type = row_get(row, "type") or "meetup"
    language = row_get(row, "language") or "en"

    return {
        # --- matches macadmins-calendar's field names exactly ---
        "name": name,
        "full_name": row_get(row, "full_name"),
        "start_date": start_date,
        "end_date": end_date,
        "location": row_get(row, "location"),
        "organizer": row_get(row, "organizer"),
        "website": website,
        "type": event_type,
        "videos": row_get(row, "videos"),
        "language": language,
        # --- NYCMA-specific ---
        "slug": slug,
        "status": status,
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
