# Setup Guide — Google Sheet → GitHub Action → Site

The Google Sheet is the events CMS. A GitHub Action pulls it as CSV on a
schedule (and on demand), regenerates `data/events.json`, and commits it —
that commit triggers the normal Hugo deploy. No Apps Script, no credentials,
no service account: the sheet is shared **"Anyone with the link" → Viewer**,
and its CSV export endpoint is a plain public URL.

```
Google Sheet (Anyone with the link: Viewer)
      │  hourly cron + workflow_dispatch
      ▼
.github/workflows/events-sync.yaml
      │  scripts/sync_events.py  (stdlib Python — fetch CSV, parse, diff)
      ▼
data/events.json  (committed only if it changed)
      │  push triggers deploy.yaml
      ▼
Hugo build ──▶ GitHub Pages
  (event pages, home listing, past archive, RSS feed)
```

## 1. The sheet

Live sheet: https://docs.google.com/spreadsheets/d/1VwqUoKC8n1I-Ao7tkOl50kusD05B0QITXvwu2kUljic/edit

Sharing must stay **Anyone with the link → Viewer** (Share button, top
right) — that's what makes the CSV export URL work without authentication.
The first tab's data is what gets pulled (`gid=0`); if you add more tabs,
keep events on the first one or update `EVENTS_SHEET_GID` (see §3).

To seed a fresh copy of the sheet instead: **File → Import → Upload** →
[`docs/events_import.csv`](events_import.csv) → import location **Replace
current sheet**.

### Column reference

| Column | Required | Notes |
|---|---|---|
| `slug` | no | URL id, e.g. `2026-07-21-july-meetup`. Auto-derived from date+title if blank. **Don't change it after publishing** (it's the RSS guid + page URL). |
| `status` | no | `published` (default) / `draft` (never synced) / `canceled` (shows a Canceled banner) |
| `title` | **yes** | Event name |
| `date` | **yes** | Event date, e.g. `7/21/2026` |
| `start` | **yes** | Time presentations start, e.g. `4:30 PM` |
| `doors` | no | Time entry/doors open, e.g. `4:00 PM` |
| `location_name` | no | Venue name |
| `address` | no | Full street address (becomes a map link) |
| `general_info` | no | Free-text logistics |
| `presentation_title` | no | Talk title |
| `presentation_info` | no | Talk abstract |
| `speakers` | no | Comma-separated: `John Mahlman, Bob Gendler` |
| `sponsor` | no | Sponsor name (shows as a chip on cards) |
| `sponsor_info` | no | Sponsor thank-you blurb |
| `signup_link` | no | Registration URL (the Register button) |
| `contact_email` | no | Defaults to info@nycmacadmins.com |

`date` + `start` (and `date` + `doors`) are combined by the sync script into
a full timestamp with the correct New York UTC offset — DST is handled
automatically (e.g. December sits at `-05:00`, July at `-04:00`).

## 2. The GitHub Action

Already set up in this repo: [`.github/workflows/events-sync.yaml`](../.github/workflows/events-sync.yaml).

- Runs **hourly** (`17 * * * *`) and on **manual dispatch**
  (Actions tab → "Sync events from Google Sheet" → Run workflow).
- Calls [`scripts/sync_events.py`](../scripts/sync_events.py), which fetches
  the sheet's CSV export, parses it, and diffs against the committed
  `data/events.json`.
- Commits **only if something changed** — no empty commits, no noise.
- The commit triggers `.github/workflows/deploy.yaml`, which rebuilds and
  redeploys the site.
- No repo secrets required — the sheet URL is public.

Latency from sheet edit to live site: usually under an hour (next cron
tick), or immediate via manual **Run workflow**.

## 3. Changing the sheet (if you ever recreate it)

If the Google Sheet is ever recreated, its ID changes. Update the default in
[`scripts/sync_events.py`](../scripts/sync_events.py) (`DEFAULT_SHEET_ID`),
or override without a code change via repo **Settings → Secrets and
variables → Actions → Variables**:

| Variable | Value |
|---|---|
| `EVENTS_SHEET_ID` | the sheet's ID from its URL |
| `EVENTS_SHEET_GID` | the tab's `gid` (default `0`, the first tab) |

Then reference them in the workflow's `env:` for the sync step if you add
variables — the script reads `EVENTS_SHEET_ID` / `EVENTS_SHEET_GID` from the
environment first, falling back to the defaults baked into the script.

## 4. Testing the sync locally

```sh
python3 scripts/sync_events.py
git diff data/events.json
```

Requires nothing beyond Python 3.9+ (stdlib only — `csv`, `urllib`,
`zoneinfo`).

## 5. Custom domain (later)

When the domain owners are on board:

1. Add a `CNAME` file at the repo root containing `nycmacadmins.com`.
2. Update `baseURL` in `hugo.yaml` to `https://nycmacadmins.com/`.
3. DNS: apex `A` records → GitHub Pages IPs (`185.199.108.153`, `.109.`,
   `.110.`, `.111.`) and `www` CNAME → the Pages host.
4. Repo **Settings → Pages → Custom domain** → `nycmacadmins.com` → wait for
   the check → **Enforce HTTPS**.

## Troubleshooting

- **Workflow runs but nothing updates** — check the Action's log for
  `sync_events.py` output; a per-row `skip:` message means that row failed
  to parse (bad date/time or missing title/date/start).
- **A field parses wrong** — the sheet's `date` must be `M/D/YYYY` (or
  `YYYY-MM-DD`); `start`/`doors` must be a bare time like `4:30 PM` or
  `16:30`.
- **Event missing from the site** — confirm `status` isn't `draft`.
- **Site didn't rebuild** — check the repo's Actions tab; `deploy.yaml` runs
  on every push to `main`, including the bot's sync commits.
