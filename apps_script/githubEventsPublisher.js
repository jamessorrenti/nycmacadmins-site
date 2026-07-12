// Publishes event data from this Google Sheet to the nycmacadmins-site GitHub
// repo as data/events.json. The Hugo site then builds event pages, the home
// page listing, and the RSS feed from that file on every push.
//
// Pattern adapted from the RipSS publisher (githubRssPublisher.js) — the
// ghUpsertFile_ helper is reused verbatim.
//
// Required Script Properties (Project Settings → Script Properties):
//   GITHUB_PAT     — fine-grained PAT with Contents: Read and write on the repo
//   GITHUB_OWNER   — repo owner (e.g. "jamessorrenti")
//   GITHUB_REPO    — repo name  (e.g. "nycmacadmins-site")
//   GITHUB_BRANCH  — branch to commit to (optional; defaults to "main")
//
// Event rows come from the `Events` tab. Column headers (row 1) are matched
// by name, so column order doesn't matter:
//   slug | status | title | start | doors | location_name | address |
//   general_info | presentation_title | presentation_info | speakers |
//   sponsor | sponsor_info | signup_link | contact_email
//
// status: published | draft | canceled
//   draft rows are never published; canceled rows are published with a
//   "canceled" banner on the site and in the feed.

var EVENTS_SHEET_NAME = "Events";
var EVENTS_TIMEZONE = "America/New_York";
var EVENTS_JSON_PATH = "data/events.json";

// --- Menu ---------------------------------------------------------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("NYCMA")
    .addItem("Publish events to site", "publishEventsMenu")
    .addItem("Validate rows", "validateEventsMenu")
    .addToUi();
}

function publishEventsMenu() {
  var result = publishEventsToGitHub();
  var ui = SpreadsheetApp.getUi();
  if (result.skipped) {
    ui.alert("Publish skipped", result.reason, ui.ButtonSet.OK);
  } else if (result.unchanged) {
    ui.alert("No changes", "events.json already matches the sheet — nothing to publish.", ui.ButtonSet.OK);
  } else {
    ui.alert("Published", result.count + " event(s) pushed to " + EVENTS_JSON_PATH +
             ".\nThe site rebuilds automatically in ~1 minute.", ui.ButtonSet.OK);
  }
}

function validateEventsMenu() {
  var issues = validateEvents_();
  var ui = SpreadsheetApp.getUi();
  if (issues.length === 0) {
    ui.alert("All good", "Every row parsed cleanly.", ui.ButtonSet.OK);
  } else {
    ui.alert("Found " + issues.length + " issue(s)", issues.join("\n"), ui.ButtonSet.OK);
  }
}

// --- Publish ------------------------------------------------------------

function publishEventsToGitHub() {
  var props = PropertiesService.getScriptProperties();
  var pat = props.getProperty("GITHUB_PAT");
  var owner = props.getProperty("GITHUB_OWNER");
  var repo = props.getProperty("GITHUB_REPO");
  var branch = props.getProperty("GITHUB_BRANCH") || "main";

  if (!pat || !owner || !repo) {
    var msg = "Missing Script Properties (GITHUB_PAT / GITHUB_OWNER / GITHUB_REPO). " +
              "Set them in Project Settings → Script Properties.";
    Logger.log(msg);
    return { skipped: true, reason: msg };
  }

  var events = readEvents_();
  var json = JSON.stringify(events, null, 2) + "\n";
  var result = ghUpsertFile_(pat, owner, repo, branch, EVENTS_JSON_PATH, json);
  Logger.log("publishEventsToGitHub: " + JSON.stringify(result));
  result.count = events.length;
  return result;
}

// Runnable from the Apps Script editor Run dropdown (mirrors RipSS's
// rssPublishGitHubSelfTest).
function eventsPublishSelfTest() {
  var result = publishEventsToGitHub();
  Logger.log("Result: " + JSON.stringify(result, null, 2));
  return result;
}

// --- Sheet reading ------------------------------------------------------

// Read the Events tab into an array of event objects, header-name matched.
// Skips drafts and rows without a title. Sorted ascending by start.
function readEvents_() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(EVENTS_SHEET_NAME);
  if (!sheet) throw new Error('Sheet tab "' + EVENTS_SHEET_NAME + '" not found.');
  var lastRow = sheet.getLastRow();
  var lastCol = Math.max(sheet.getLastColumn(), 1);
  if (lastRow < 2) return [];
  var values = sheet.getRange(1, 1, lastRow, lastCol).getValues();
  var header = values[0].map(function (h) { return String(h == null ? "" : h).trim().toLowerCase(); });

  function col(name) { return header.indexOf(name); }
  function cell(row, name) {
    var i = col(name);
    return i === -1 ? "" : row[i];
  }
  function text(row, name) {
    return String(cell(row, name) == null ? "" : cell(row, name)).trim();
  }

  var out = [];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var title = text(row, "title");
    if (!title) continue;

    var status = (text(row, "status") || "published").toLowerCase();
    if (status === "draft") continue;

    var start = isoDate_(cell(row, "start"));
    if (!start) {
      Logger.log("Row " + (r + 1) + ' ("' + title + '") skipped: bad/missing start date.');
      continue;
    }

    var slug = text(row, "slug") || deriveSlug_(start, title);

    out.push({
      slug: slug,
      status: status,
      title: title,
      start: start,
      doors: isoDate_(cell(row, "doors")) || "",
      location_name: text(row, "location_name"),
      address: text(row, "address"),
      general_info: text(row, "general_info"),
      presentation_title: text(row, "presentation_title"),
      presentation_info: text(row, "presentation_info"),
      speakers: text(row, "speakers")
        .split(",")
        .map(function (s) { return s.trim(); })
        .filter(Boolean),
      sponsor: text(row, "sponsor"),
      sponsor_info: text(row, "sponsor_info"),
      signup_link: text(row, "signup_link"),
      contact_email: text(row, "contact_email"),
    });
  }

  out.sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : 0; });
  return out;
}

// Coerce a cell value (Date object or ISO-ish string) to ISO 8601 with the
// New York offset. Returns "" if unparseable.
function isoDate_(v) {
  if (v == null || v === "") return "";
  if (Object.prototype.toString.call(v) === "[object Date]") {
    if (isNaN(v.getTime())) return "";
    return Utilities.formatDate(v, EVENTS_TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX");
  }
  var s = String(v).trim();
  var d = new Date(s);
  if (isNaN(d.getTime())) return "";
  // Already ISO with offset? Pass through unchanged.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/.test(s)) return s;
  return Utilities.formatDate(d, EVENTS_TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX");
}

// "2026-07-21T16:30:00-04:00" + "NYC Mac Admins July 2026 Meetup"
//   → "2026-07-21-nyc-mac-admins-july-2026-meetup"
function deriveSlug_(isoStart, title) {
  var datePart = isoStart.substring(0, 10);
  var titlePart = title.toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return datePart + "-" + titlePart;
}

// --- Validation ---------------------------------------------------------

function validateEvents_() {
  var issues = [];
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(EVENTS_SHEET_NAME);
  if (!sheet) return ['Missing tab "' + EVENTS_SHEET_NAME + '".'];
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return ["No event rows."];
  var values = sheet.getRange(1, 1, lastRow, sheet.getLastColumn()).getValues();
  var header = values[0].map(function (h) { return String(h || "").trim().toLowerCase(); });

  ["title", "start"].forEach(function (req) {
    if (header.indexOf(req) === -1) issues.push('Missing required column "' + req + '".');
  });
  if (issues.length) return issues;

  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var rowNum = r + 1;
    var title = String(row[header.indexOf("title")] || "").trim();
    if (!title) { issues.push("Row " + rowNum + ": no title (row will be skipped)."); continue; }
    if (!isoDate_(row[header.indexOf("start")])) issues.push("Row " + rowNum + ": start date won't parse.");
    var iStatus = header.indexOf("status");
    if (iStatus !== -1) {
      var st = String(row[iStatus] || "published").trim().toLowerCase();
      if (["published", "draft", "canceled"].indexOf(st) === -1) {
        issues.push("Row " + rowNum + ': status "' + st + '" is not published/draft/canceled.');
      }
    }
    var iLink = header.indexOf("signup_link");
    if (iLink !== -1) {
      var link = String(row[iLink] || "").trim();
      if (link && !/^https?:\/\//.test(link)) issues.push("Row " + rowNum + ": signup_link is not a URL.");
    }
  }
  return issues;
}

// --- GitHub Contents API (reused from RipSS githubRssPublisher.js) -------

// Create or update a file via the GitHub Contents API. If the file exists,
// we GET it first to capture its sha (required for updates). Skips the PUT
// entirely when the existing content already matches (no empty commits).
function ghUpsertFile_(pat, owner, repo, branch, path, content) {
  var url = "https://api.github.com/repos/" + encodeURIComponent(owner) +
            "/" + encodeURIComponent(repo) + "/contents/" + encodeURIComponent(path);
  var headers = {
    "Authorization": "token " + pat,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "nycmacadmins-events/apps-script",
  };

  // Look up existing sha (if file exists).
  var sha = null;
  var getResp = UrlFetchApp.fetch(url + "?ref=" + encodeURIComponent(branch), {
    method: "get",
    headers: headers,
    muteHttpExceptions: true,
  });
  var getCode = getResp.getResponseCode();
  if (getCode === 200) {
    var meta = JSON.parse(getResp.getContentText());
    sha = meta.sha;
    // Skip the commit when nothing changed.
    var existing = Utilities.newBlob(Utilities.base64Decode(meta.content.replace(/\n/g, ""))).getDataAsString();
    if (existing === content) {
      return { status: 200, unchanged: true };
    }
  } else if (getCode === 404) {
    // New file — no sha needed for PUT.
  } else {
    throw new Error("GET " + path + " returned " + getCode + ": " +
                    getResp.getContentText().substring(0, 300));
  }

  var payload = {
    message: "Sync events from sheet — " + new Date().toISOString(),
    content: Utilities.base64Encode(content, Utilities.Charset.UTF_8),
    branch: branch,
  };
  if (sha) payload.sha = sha;

  var putResp = UrlFetchApp.fetch(url, {
    method: "put",
    contentType: "application/json",
    headers: headers,
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  var putCode = putResp.getResponseCode();
  if (putCode < 200 || putCode >= 300) {
    throw new Error("PUT " + path + " returned " + putCode + ": " +
                    putResp.getContentText().substring(0, 300));
  }
  return { status: putCode, created: !sha, updated: !!sha };
}
