# nycmacadmins-site

Community site for **NYC Mac Admins** — meetups for the people who manage
Apple devices in and around New York City.

- **Live site:** https://nycmacadmins.com/
- **Events RSS feed:** https://nycmacadmins.com/events/index.xml
- **Community:** [#newyork](https://macadmins.slack.com/archives/C3APLCT1R) on the [Mac Admins Slack](https://www.macadmins.org/) · info@nycmacadmins.com

## How it works

```
Google Sheet ("Anyone with the link" viewer, public CSV export)
      │  hourly cron + workflow_dispatch
      ▼
.github/workflows/events-sync.yaml → scripts/sync_events.py
      │  fetches CSV, parses, commits data/events.json only if changed
      ▼
push triggers .github/workflows/deploy.yaml
      ▼
Hugo build ──▶ GitHub Pages
  ├─ home page: upcoming events
  ├─ /events/<slug>/ — one page per event
  ├─ /events/ — past-meetups archive
  └─ /events/index.xml — RSS feed
```

- Events are edited in a **Google Sheet** — no git, no Apps Script, no
  credentials. See **[docs/SETUP.md](docs/SETUP.md)** for the column
  reference and how the sync works;
  [docs/events_import.csv](docs/events_import.csv) seeds a fresh sheet.
- [`scripts/sync_events.py`](scripts/sync_events.py) is stdlib-only Python —
  no dependencies to install.
- [`content/events/_content.gotmpl`](content/events/_content.gotmpl) turns
  `data/events.json` into pages at build time; no per-event markdown files.

## Local development

```sh
brew install hugo        # extended edition
hugo server              # http://localhost:1313/
```

Edit `data/events.json` directly for local testing, or run
`python3 scripts/sync_events.py` to pull the live sheet. In production
`events.json` is overwritten by the hourly sync, so real event changes go in
the sheet, not this file.

## Site structure

| Path | What |
|---|---|
| `hugo.yaml` | Site config (buildFuture is required — events are future-dated) |
| `layouts/` | Templates: home, event single/list, RSS (`_default/rss.xml`) |
| `static/css/main.css` | Design tokens: NYC subway yellow `#F4CE47`, blue `#314FA6`, ink `#111214`; Oswald (display) + Lato (body) |
| `static/fonts/` | Self-hosted woff2 (OFL licenses included) |
| `content/*.md` | About, Code of Conduct, Speakers, Sponsors |
| `docs/` | Setup guide + sheet seed CSV |

## Deploying

Push to `main` → `.github/workflows/deploy.yaml` builds with Hugo and deploys
to GitHub Pages. Repo **Settings → Pages → Source** must be set to
**GitHub Actions** (one time).
