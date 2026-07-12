# NYC Mac Admins — Community Site Build Plan

A community site for **NYCmacadmins.com**, built the same way as `~/src/above-site`
(Hugo + GitHub Pages, deployed by GitHub Actions), themed from the **NYCMA July 2026**
deck and logo, with meetup events driven by a **Google Sheet → RSS feed** pipeline.

- **Repo folder:** `~/src/nycmacadmins-site`
- **Custom domain:** `nycmacadmins.com` (GitHub Pages + `CNAME`)
- **Generator:** Hugo (extended), matching the reference site's stack and deploy flow
- **Event source of truth:** a Google Sheet → a bound Apps Script pushes `data/events.json` to the repo (RipSS pattern); Hugo builds the pages + RSS

---

## 1. Goals

1. A clean, fast, static marketing/community site for the NYC Mac Admins meetup.
2. Event listings (upcoming + past) that non-developers can edit in a **Google Sheet**.
3. A public **RSS feed** of events, regenerated when an editor publishes from the sheet
   (RipSS-style bound Apps Script pushes the data; Hugo builds the feed).
4. Each event captures: **name, date, address, general info, presentation info, sponsor info, sign-up link** (plus speakers, doors time, contact).
5. Zero-cost hosting on GitHub Pages, one-command local preview, push-to-deploy.

---

## 2. Branding & Theming (from the deck + logo)

Extracted directly from `NYCMA-26-July.pdf` and `Logo/NYC-Mac-Admins.png`.

### Colors (exact hex sampled from the logo)

| Token | Hex | Use |
|-------|-----|-----|
| `--nyc-yellow` | `#F4CE47` | Primary accent (the "N" dot, "JULY 2026" text, buttons/highlights) |
| `--nyc-blue`   | `#314FA6` | Secondary accent (the "C" dot, links, sponsor tags) |
| `--nyc-ink`    | `#111214` | Text / the "Y" dot / logo outline (near-black) |
| `--nyc-bg`     | `#FFFFFF` | Page background |
| `--nyc-bg-soft`| `#F5F6F8` | Alternating sections / cards |
| `--nyc-line`   | `rgba(17,18,20,0.12)` | Hairlines / borders |
| `--nyc-muted`  | `#5A5F66` | Secondary text |

**Motif:** desaturated / black-and-white **NYC skyline photography** (Statue of Liberty +
Lower Manhattan, as on the title slide) with the yellow + blue + black brand marks laid over it.
The hero should echo the deck: grayscale cityscape, bold display type, a yellow date/eyebrow.

### Typography (all present in `Other Assets/NYCMA-fonts/`, all Google Fonts / OFL)

Available families: **Lato, Montserrat, Oswald, Playfair Display, Quantico, Sen, Urbanist.**

Recommended two-font system (matches the deck's condensed display + clean body):

| Role | Font | Notes |
|------|------|-------|
| Display / H1–H3 / eyebrows | **Oswald** | Condensed, bold — matches "JULY 2026" and the poster feel |
| Body / UI / nav | **Lato** | Highly readable, full static weight set provided |
| (Optional) wordmark accent | **Sen** or **Urbanist** | Geometric, echoes the "MAC ADMINS" wordmark |

- **Delivery:** self-host from the provided TTFs in `static/fonts/` with `@font-face` (keeps
  the site fully static and offline-capable), **or** load from Google Fonts CDN like `above-site`
  does. Plan uses **self-hosted** to avoid a third-party dependency and match the supplied assets.

### Logo assets

- Source: `~/Desktop/NYCMA/Logo/NYC-Mac-Admins.png` (raster) + `NYC-Mac-Admins.af` (Affinity source).
- Deliverables to generate into `static/images/`:
  - `logo.png` (header, ~2x for retina) and an `logo.svg` if we can export from Affinity.
  - `favicon.svg` / `favicon.png` (the rounded-square NYC mark).
  - `og-image.png` (1200×630 social card using the skyline + logo).

---

## 3. Tech Stack & Repo Structure

Mirror `above-site` exactly where possible so the two repos stay maintainable together.

```
nycmacadmins-site/
├─ .github/workflows/
│  └─ deploy.yaml            # Hugo build + Pages deploy (copied from above-site)
│                            #   (no events-sync workflow — Apps Script pushes data; see §5)
├─ content/
│  ├─ _index.md              # home page metadata
│  ├─ about.md
│  ├─ code-of-conduct.md
│  ├─ sponsors.md
│  └─ events/
│     └─ _content.gotmpl     # content adapter: builds one page per event from data/events.json
├─ data/
│  └─ events.json            # ← PUSHED by Apps Script from the sheet (single source of truth)
├─ layouts/
│  ├─ index.html             # home (hero, next event, UPCOMING list inline, sponsors, CTA)
│  ├─ _default/
│  │  ├─ baseof.html
│  │  └─ single.html         # generic page
│  ├─ events/
│  │  ├─ single.html         # full event page (date, address, talk, sponsor, signup)
│  │  └─ list.html           # /events/past/ archive (past events, newest-first)
│  ├─ partials/
│  │  ├─ header.html
│  │  ├─ footer.html
│  │  └─ event-card.html
│  └─ _default/
│     └─ rss.xml             # custom RSS template → the public events feed
├─ static/
│  ├─ css/main.css           # design tokens above
│  ├─ js/main.js
│  ├─ fonts/                 # self-hosted TTFs
│  └─ images/                # logo, favicon, og-image, skyline
├─ apps_script/              # source-of-record for the bound Apps Script (mirrors RipSS)
│  ├─ githubEventsPublisher.js  # reads sheet → pushes data/events.json via GitHub Contents API
│  └─ appsscript.json
├─ hugo.yaml
├─ .gitignore
└─ README.md
```

> `CNAME` is added later (Phase 5, §6) — the temporary publish runs on the Pages URL.

### Pages / sections

- **Home** (`layouts/index.html`): grayscale-skyline hero with logo + tagline; a featured
  **Next meetup** card (soonest upcoming event); then **all upcoming events listed right on the
  main page** (from `data/events.json`, `start >= now`, sorted soonest-first). A **"Past events"**
  link/button sits at the end of the list and goes to `/events/past/`. Below the list: sponsor
  logos and a "Join us" CTA with community links (see §3.1).
- **Events archive** (`/events/past/`): past meetups only (`start < now`), newest-first.
  (Upcoming events live on the home page, so there's no separate "upcoming" list page.)
- **Event detail** (`/events/<slug>/`): name, date/time, doors, address (+ map link), general
  info, presentation title/abstract, speakers, sponsor + sponsor info, **Register** button.
- **About / Code of Conduct / Sponsors**: static markdown pages.
- **RSS**: `/feed.xml` linked in the `<head>` and footer.

### 3.1 Community links (confirmed)

Surface these in the header CTA / footer / "Join us" section:

- **Slack org:** [macadmins.org](https://www.macadmins.org/) (Mac Admins Slack sign-up).
- **Channel:** **#newyork** — deep link `https://macadmins.slack.com/archives/C3APLCT1R`
  (channel ID `C3APLCT1R`). Primary "get involved" CTA.
- Contact: `info@nycmacadmins.com`.
- (Others TBD per §9.4 — GitHub, Bluesky/X, mailing list if wanted.)

---

## 4. Event Data Model & Google Sheet Schema

One meetup = one row. Column headers (row 1 of the sheet) map 1:1 to the fields requested.

| Column | Example | Notes |
|--------|---------|-------|
| `slug` | `2026-07-21-july-meetup` | Stable id → URL + filename. If blank, derived from date+title. |
| `status` | `published` | `published` \| `draft` \| `canceled`. Only `published` rows are synced. |
| `title` | `NYC Mac Admins July 2026 Meetup` | Event name |
| `start` | `2026-07-21T16:30:00-04:00` | ISO 8601 w/ NYC offset — the "starts at 4:30 PM" time |
| `doors` | `2026-07-21T16:00:00-04:00` | Optional — "entry begins at 4:00pm" |
| `location_name` | `11 Pennsylvania Plaza` | Venue name |
| `address` | `11 Pennsylvania Plaza, New York, NY 10001` | Full address (used for map link) |
| `general_info` | `Entry begins at 4:00pm; presentations begin at 4:30pm.` | Free text |
| `presentation_title` | `mSCP 2.0` | Talk title |
| `presentation_info` | `John Mahlman (@jmahlman) and Bob Gendler (@boberito) discuss the new mSCP 2.0 release…` | Talk abstract |
| `speakers` | `John Mahlman (@jmahlman), Bob Gendler (@boberito)` | Comma-separated |
| `sponsor` | `Addigy` | Sponsor name |
| `sponsor_info` | `Thanks to Addigy for providing food and refreshments.` | Sponsor blurb |
| `signup_link` | `https://forms.gle/nqDXZ9GqR8J6JmA5A` | Registration URL |
| `contact_email` | `info@nycmacadmins.com` | Optional per-event contact |

### Starter CSV to import (`events_import.csv`)

I'll deliver this file ready to **File → Import → Upload** into a new Google Sheet
(import location: *Replace current sheet*, so headers land in row 1):

```csv
slug,status,title,start,doors,location_name,address,general_info,presentation_title,presentation_info,speakers,sponsor,sponsor_info,signup_link,contact_email
2026-07-21-july-meetup,published,NYC Mac Admins July 2026 Meetup,2026-07-21T16:30:00-04:00,2026-07-21T16:00:00-04:00,11 Pennsylvania Plaza,"11 Pennsylvania Plaza, New York, NY 10001","Entry begins at 4:00pm with presentations and discussions beginning at 4:30pm.",mSCP 2.0,"John Mahlman (@jmahlman) and Bob Gendler (@boberito) discuss the new mSCP 2.0 release, which provides a unified codebase that eliminates the need for separate branches per macOS version. The macOS Security Compliance Project (mSCP) is an open source effort to provide a programmatic approach to generating security guidance for macOS.","John Mahlman (@jmahlman), Bob Gendler (@boberito)",Addigy,"Thanks to this month's sponsor, Addigy, for providing food and refreshments.",https://forms.gle/nqDXZ9GqR8J6JmA5A,info@nycmacadmins.com
```

---

## 5. Sheet → Site → RSS Architecture (mirrors RipSS)

This follows the **proven RipSS pattern** (`product-launch-comms-processor/sheets/master-visualizer/githubRssPublisher.js`
→ `jamessorrenti/RipSS`): the Google Sheet is the CMS, and a **bound Apps Script pushes the data
straight to the GitHub repo via the Contents API.** No repo secrets, no cron, no CI pull — the
PAT lives only in Apps Script. The difference from RipSS: our target repo is a **Hugo** site, so
Apps Script pushes **`data/events.json`** and lets Hugo render pages + the RSS feed (RipSS pushes
finished `.xml` because it has no build step).

```
Google Sheet (Events + _Config tabs)
        │   editor clicks  NYCMA ▸ Publish events   (or an onEdit trigger)
        ▼
Apps Script  githubEventsPublisher.js   (reuses RipSS's ghUpsertFile_ verbatim)
        │   • read Events tab → build events[] (published rows, sorted by start)
        │   • PUT data/events.json to the repo via GitHub Contents API
        ▼
push to main ─▶ existing deploy.yaml ─▶ Hugo build ─▶ GitHub Pages
                                             │
                                             ├─ home: upcoming events inline
                                             ├─ /events/<slug>/ pages (content adapter)
                                             ├─ /events/past/ archive
                                             └─ RSS feed (custom rss.xml template)
```

**Why this over a GitHub Action pulling CSV:** it's the pattern you already run in production
(RipSS), keeps the GitHub token out of the repo entirely, needs no schedule (updates the moment
the editor publishes), and reuses `ghUpsertFile_` as-is.

### 5.1 Apps Script — `githubEventsPublisher.js` (adapted from RipSS)

Bound to the events spreadsheet. Config in **Script Properties** (same names/idea as RipSS):
`GITHUB_PAT` (fine-grained, Contents: R/W on `nycmacadmins-site`), `GITHUB_OWNER`,
`GITHUB_REPO`, `GITHUB_BRANCH` (default `main`).

- `readEvents_()` — read the `Events` tab by header name (tolerant of column order, like
  RipSS's `readFeedsConfig_()`); keep `status == published`; coerce `start`/`doors` to ISO;
  split `speakers` on commas; sort ascending by `start`.
- `publishEventsToGitHub()` — serialize `events[]` to JSON and **`ghUpsertFile_(pat, owner,
  repo, branch, "data/events.json", json)`** — the exact GET-sha-then-PUT helper copied from
  `githubRssPublisher.js` (already handles create vs. update and base64).
- `onOpen()` — add a **"NYCMA ▸ Publish events"** menu item (mirrors RipSS's manual
  `rssPublishGitHubSelfTest`) plus a self-test that logs the result.
- Optional installable `onEdit(e)` trigger (debounced) so publishing is automatic on edit.
- **PAT handling:** you create the fine-grained PAT and paste it into Script Properties
  yourself — I provide the script + step-by-step, but never handle the token. (Same as your
  current RipSS setup.)

> Reuse note: `ghUpsertFile_`, the Script-Properties config approach, the menu/self-test, and
> the "sheet is the single source of truth" model all come straight from your working RipSS
> publisher — we're only swapping *what* gets generated (events JSON vs. product RSS XML).

### 5.2 Hugo side — pages + RSS from `data/events.json`

- **Content adapter** `content/events/_content.gotmpl` (Hugo ≥ 0.126; deploy uses 0.139) reads
  `site.Data.events` and emits one page per event at `/events/<slug>/` — no per-event markdown
  files to push or garbage-collect. `layouts/events/single.html` renders name, date/time, doors,
  address (+ Google Maps link), general info, presentation title/abstract, speakers, sponsor +
  sponsor info, and the **Register** button.
- **Home** (`index.html`) and **`/events/past/`** (`list.html`) read the same data and filter on
  `start` vs. `now`.
- **RSS**: a custom `layouts/_default/rss.xml` renders the events feed (per item: title, event
  page link, `guid`, `pubDate` = event start, and a description combining date, address, talk,
  sponsor, and sign-up link). Output at a stable path (e.g. `/events/index.xml`), linked in
  `<head>` + footer. This is the public "Sheet → RSS" feed, produced on every publish.

> **Alternative (full RipSS parity):** if you'd rather the feed be byte-generated by Apps Script
> exactly like RipSS, the script can also build `static/feed.xml` and `ghUpsertFile_` it
> alongside `events.json`. Default is Hugo-native RSS (far less code); say the word to switch.

### 5.3 Getting data out of the sheet

None needed as a public URL — Apps Script reads the sheet **directly** (it's bound to it) and
pushes JSON. The sheet can stay **private**; only the generated `events.json` on GitHub is public.
(This is strictly simpler than the "publish sheet to web as CSV" approach and avoids exposing the
raw sheet.)

---

## 6. Deployment (GitHub Pages)

**Phase 1 — temporary publish on the GitHub Pages URL (no custom domain yet):**

1. Create GitHub repo `nycmacadmins-site` under your account; push `main`.
2. **Settings → Pages → Source: GitHub Actions** (same as `above-site`).
3. **No `CNAME` file yet.** Site serves at the project-pages URL
   `https://<user>.github.io/nycmacadmins-site/`. The `deploy.yaml` already builds with
   `--baseURL "${{ steps.pages.outputs.base_url }}/"`, so the subpath is handled automatically —
   all asset/links must use Hugo's `relURL`/`relref` (they do) so nothing hardcodes the domain.
4. Add repo **secret** `EVENTS_CSV_URL` (the published-sheet CSV URL).
5. First `deploy.yaml` run builds + publishes; `events-sync.yaml` populates events on schedule.

**Phase 2 — custom domain (later, after talking to the domain owners, per §9.5):**

6. Add `CNAME` file `nycmacadmins.com`; at the registrar set apex `A`/`AAAA` → GitHub Pages IPs
   (or `ALIAS`/`ANAME` → `<user>.github.io`) and `www` `CNAME` → `<user>.github.io`;
   enable **Enforce HTTPS**. No code change needed beyond adding `CNAME`.

---

## 7. Build Phases / Checklist

**Phase 0 — Scaffold**
- [ ] `hugo new site` structure in `~/src/nycmacadmins-site`; copy `.gitignore`, `deploy.yaml`, `hugo.yaml` base from `above-site` and rename to NYCMA.
- [ ] `git init`, initial commit.

**Phase 1 — Theme**
- [ ] Add brand tokens (colors above) + self-hosted Oswald/Lato in `static/fonts` + `@font-face`.
- [ ] Process logo → `logo.png/svg`, `favicon`, `og-image` (skyline + mark).
- [ ] Build `baseof.html`, `header.html`, `footer.html`, `main.css`, `main.js` (adapted from `above-site`).

**Phase 2 — Content & layouts**
- [ ] Home `index.html` (hero, next event, recent events, sponsors, CTA).
- [ ] `events/single.html` + `list.html` + `event-card.html`.
- [ ] `about.md`, `code-of-conduct.md`, `sponsors.md`.

**Phase 3 — Events data pipeline (RipSS-style)**
- [ ] Deliver `events_import.csv` (with the July 2026 row) — you import to a new Google Sheet (`Events` tab); add a `_Config` tab.
- [ ] Add `content/events/_content.gotmpl` + `layouts/events/single.html`, `list.html`, `_default/rss.xml`; verify pages + feed build from a checked-in sample `data/events.json`.
- [ ] Add Apps Script `githubEventsPublisher.js` (reusing `ghUpsertFile_`); set Script Properties (`GITHUB_PAT`, `GITHUB_OWNER`, `GITHUB_REPO`) — **you** paste the PAT.
- [ ] Run **NYCMA ▸ Publish events**; confirm `data/events.json` lands in the repo and `deploy.yaml` rebuilds.
- [ ] (Optional) Add debounced `onEdit` trigger for auto-publish on edit.

**Phase 4 — Ship (temporary GitHub Pages URL)**
- [ ] Publish at `https://<user>.github.io/nycmacadmins-site/` (no custom domain yet).
- [ ] Verify home shows upcoming events, `/events/past/`, `/events/2026-07-21-july-meetup/`, and `/feed.xml` in an RSS reader.

**Phase 5 — Custom domain (later)**
- [ ] After talking to domain owners: add `CNAME`, point `nycmacadmins.com` DNS at Pages, enable HTTPS.

---

## 8. Deliverables I will produce when we build

1. Full Hugo site (layouts, `main.css` with the brand tokens, JS, self-hosted fonts, logo/favicon/OG).
2. **`events_import.csv`** — ready to import into the sheet's `Events` tab, pre-loaded with the July 2026 meetup.
3. **`content/events/_content.gotmpl`** + event layouts + **`layouts/_default/rss.xml`** — pages & RSS from `data/events.json`.
4. Copied **`.github/workflows/deploy.yaml`** (Hugo build + Pages). *No events-sync workflow — Apps Script pushes the data.*
5. **`apps_script/githubEventsPublisher.js`** (+ `appsscript.json`) reusing RipSS's `ghUpsertFile_`, plus a step-by-step setup doc (Script Properties, PAT, menu/trigger).
6. `README.md` covering local preview (`hugo server`), editing events in the sheet, and the later DNS step.

---

## 9. Decisions (resolved)

1. **Fonts:** ✅ **Oswald (display) + Lato (body)**, self-hosted.
2. **Pipeline:** ✅ **RipSS-style — bound Apps Script pushes `data/events.json` to the repo**
   (reuses `ghUpsertFile_`). Sheet stays **private**; no repo secrets; no CSV publish; no cron.
3. **Publishing:** ✅ **manual "NYCMA ▸ Publish events" menu** to start (matches RipSS's manual
   `rssPublishGitHubSelfTest`); optional debounced `onEdit` auto-publish can be added later.
4. **Community links:** ✅ **Slack org [macadmins.org](https://www.macadmins.org/)** + **#newyork**
   (`C3APLCT1R`, `https://macadmins.slack.com/archives/C3APLCT1R`) as the primary CTA; email
   `info@nycmacadmins.com`. GitHub/social/mailing list can be added later if wanted.
5. **Domain:** ✅ **Temp-publish on the GitHub Pages URL only.** Custom `nycmacadmins.com`
   deferred until after talking to the domain owners (Phase 5 / §6).
6. **Events on site:** ✅ **Upcoming events listed on the home page**; a **"Past events"**
   link opens `/events/past/` (archive, newest-first).
```
