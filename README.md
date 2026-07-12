# nycmacadmins-site

Community site for **NYC Mac Admins** — meetups for the people who manage
Apple devices in and around New York City.

- **Live site:** https://nycmacadmins.com/
- **Events RSS feed:** https://nycmacadmins.com/events/index.xml
- **Community:** [#newyork](https://macadmins.slack.com/archives/C3APLCT1R) on the [Mac Admins Slack](https://www.macadmins.org/) · info@nycmacadmins.com

## How it works

```
Google Sheet (events CMS, private)
      │  NYCMA ▸ Publish events to site   (Apps Script menu)
      ▼
data/events.json  (pushed via GitHub Contents API)
      │  push triggers .github/workflows/deploy.yaml
      ▼
Hugo build ──▶ GitHub Pages
  ├─ home page: upcoming events
  ├─ /events/<slug>/ — one page per event
  ├─ /events/ — past-meetups archive
  └─ /events/index.xml — RSS feed
```

- Events are edited in a **Google Sheet** — no git required for organizers.
  See **[docs/SETUP.md](docs/SETUP.md)** for the one-time pipeline setup and
  the column reference; [docs/events_import.csv](docs/events_import.csv) seeds
  the sheet.
- The Apps Script lives in [apps_script/](apps_script/) (source of record —
  paste into the sheet's Script editor).
- [`content/events/_content.gotmpl`](content/events/_content.gotmpl) turns
  `data/events.json` into pages at build time; no per-event markdown files.

## Local development

```sh
brew install hugo        # extended edition
hugo server              # http://localhost:1313/
```

Edit `data/events.json` directly for local testing — in production it is
overwritten by the sheet publish, so real event changes go in the sheet.

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
