# Setup Guide — Google Sheet → GitHub → Site

One-time setup for the events pipeline. When you're done, editing the Google
Sheet and clicking **NYCMA ▸ Publish events to site** updates the website and
RSS feed automatically.

```
Google Sheet ──(Apps Script menu)──▶ data/events.json in this repo
                                          │
                              push triggers deploy.yaml
                                          ▼
                          Hugo build ──▶ GitHub Pages
                          (event pages, home listing, RSS feed)
```

## 1. Create the Google Sheet

1. Create a new Google Sheet (any name, e.g. **NYCMA Events**).
2. Rename the first tab to **`Events`** (exact name, capital E).
3. **File → Import → Upload** → select [`docs/events_import.csv`](events_import.csv)
   from this repo → Import location: **Replace current sheet**.
   - Headers land in row 1; the July 2026 meetup is row 2.
4. The sheet can stay **private** — the script reads it directly.

### Column reference

| Column | Required | Notes |
|---|---|---|
| `slug` | no | URL id, e.g. `2026-07-21-july-meetup`. Auto-derived from date+title if blank. **Don't change it after publishing** (it's the RSS guid + URL). |
| `status` | no | `published` (default) / `draft` (never published) / `canceled` (shows a Canceled banner) |
| `title` | **yes** | Event name |
| `start` | **yes** | Presentations start. A normal Sheets date-time (e.g. `7/21/2026 16:30`) or ISO `2026-07-21T16:30:00-04:00` — both work |
| `doors` | no | Entry/doors-open time, same formats |
| `location_name` | no | Venue name |
| `address` | no | Full street address (becomes a map link) |
| `general_info` | no | Free-text logistics ("Entry begins at 4:00pm…") |
| `presentation_title` | no | Talk title |
| `presentation_info` | no | Talk abstract |
| `speakers` | no | Comma-separated: `John Mahlman (@jmahlman), Bob Gendler (@boberito)` |
| `sponsor` | no | Sponsor name (shows as a chip on cards) |
| `sponsor_info` | no | Sponsor thank-you blurb |
| `signup_link` | no | Registration URL (the Register button) |
| `contact_email` | no | Defaults to info@nycmacadmins.com |

## 2. Add the Apps Script

1. In the sheet: **Extensions → Apps Script**.
2. Delete the default `Code.gs` content and paste in
   [`apps_script/githubEventsPublisher.js`](../apps_script/githubEventsPublisher.js).
3. (Optional) **Project Settings → check "Show appsscript.json"** and replace it
   with [`apps_script/appsscript.json`](../apps_script/appsscript.json).
4. Save. Reload the spreadsheet — an **NYCMA** menu appears.

## 3. Create the GitHub token (you do this part)

1. GitHub → **Settings → Developer settings → Fine-grained personal access tokens → Generate new token**.
2. Name: `nycma-events-publisher`. Expiration: your call (set a calendar
   reminder if it expires).
3. **Repository access:** Only select repositories → `nycmacadmins-site`.
4. **Permissions → Repository permissions → Contents: Read and write.** Nothing else.
5. Generate and copy the token.

## 4. Configure Script Properties

In the Apps Script editor: **Project Settings (gear) → Script Properties → Add
script property**:

| Property | Value |
|---|---|
| `GITHUB_PAT` | the token from step 3 |
| `GITHUB_OWNER` | `jamessorrenti` |
| `GITHUB_REPO` | `nycmacadmins-site` |
| `GITHUB_BRANCH` | `main` (optional — this is the default) |

The token lives **only** here — never in the repo.

## 5. First publish

1. In the sheet: **NYCMA ▸ Validate rows** — fix anything it flags.
2. **NYCMA ▸ Publish events to site** — first run asks you to authorize the
   script (it needs: read this spreadsheet, call an external service).
3. Check the repo: `data/events.json` should have a fresh commit
   ("Sync events from sheet — …"), and the **Deploy Hugo site to Pages**
   action should be running.

Publishing is idempotent — if the sheet matches what's already on GitHub, the
script skips the commit ("No changes").

## 6. GitHub Pages (one time, in the repo)

1. Push this repo to GitHub as `nycmacadmins-site`.
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. First push to `main` deploys to
   `https://jamessorrenti.github.io/nycmacadmins-site/`.

## 7. Custom domain (later)

When the domain owners are on board:

1. Add a `CNAME` file at the repo root containing `nycmacadmins.com`.
2. Update `baseURL` in `hugo.yaml` to `https://nycmacadmins.com/`.
3. DNS: apex `A` records → GitHub Pages IPs (`185.199.108.153`, `.109.`, `.110.`, `.111.`)
   and `www` CNAME → `jamessorrenti.github.io`.
4. Repo **Settings → Pages → Custom domain** → `nycmacadmins.com` → wait for
   the check → **Enforce HTTPS**.

## Optional: auto-publish on edit

The manual menu matches how RipSS works and avoids publishing half-edited
rows. If you later want edits to publish automatically:

- Apps Script editor → **Triggers (clock icon) → Add Trigger** →
  function `publishEventsToGitHub`, event source **From spreadsheet**,
  event type **On change**.
- Consider keeping rows as `draft` while editing so half-finished events
  never go live.

## Troubleshooting

- **"Publish skipped: missing Script Properties"** — step 4 wasn't completed.
- **`PUT data/events.json returned 401/403`** — PAT expired or lacks
  Contents: Read and write on this repo. Make a new one (step 3).
- **Event missing from the site** — check `status` isn't `draft`, the `start`
  date parses (**NYCMA ▸ Validate rows**), and the row has a `title`.
- **Site didn't rebuild** — check the repo's Actions tab; the deploy workflow
  runs on every push to `main`.
