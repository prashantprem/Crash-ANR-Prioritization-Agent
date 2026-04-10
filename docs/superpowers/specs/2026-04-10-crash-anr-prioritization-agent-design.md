# Crash & ANR Prioritization Agent — POC Design

**Date:** 2026-04-10  
**Author:** Prashant  
**Status:** Design approved, pending implementation  
**POC Repo:** Personal GitHub (to be created)  
**Target:** Pitch to Pocket FM Android team after POC is working

---

## Goal

Build an agent that automatically fetches crash and ANR data from Firebase Crashlytics, detects fresh issues (new in current version), detects spikes in existing issues, tracks session health trends, prioritizes everything by user impact, correlates fresh crashes to the GitHub PRs that introduced them, generates LLM fix suggestions for all issues, and publishes a daily HTML report to GitHub Pages — all using free services.

---

## Scope (POC)

- **Issue source:** Firebase Crashlytics REST API (personal Firebase project) — fetches both `type=CRASH` and `type=ANR` issues in one pass
- **ANR detection:** Issues where the Crashlytics `type` field is annotated `ANR` (no special stack parsing needed — the annotation is authoritative)
- **Output:** Static HTML report hosted on GitHub Pages
- **Fresh issue definition:** Issue signature (stack hash / issue ID) that appears in version N but was absent in version N-1
- **Spike definition:** An existing issue whose event rate in the last 24h exceeds 2× its 7-day rolling daily average
- **Session health:** Crash-free sessions % and ANR-free sessions % fetched from GA4 Data API, trended over 30 days
- **PR correlation:** GitHub REST API — only for FRESH issues — finds PRs whose commits last touched the files in the crash stack trace
- **Fix suggestions:** Gemini 1.5 Flash API (free tier) — runs for ALL issues (fresh and non-fresh)
- **Runner:** GitHub Actions (scheduled daily)

---

## Architecture

```
GitHub Actions (scheduled daily @ 9 AM)
│
├─ Step 1: CrashFetcher
│     Firebase Crashlytics REST API (service account auth)
│     → Fetch all issues for version N (current) and version N-1 (previous)
│     → Each issue has: id, type (CRASH|ANR), signature, eventCount,
│        affectedUsers, firstSeenVersion, lastSeenTime
│
├─ Step 2: FreshIssueDetector
│     Compare issue signatures between version N and N-1
│     → Tag any signature absent in N-1 as FRESH=true
│
├─ Step 3: SpikeDetector
│     For each issue not tagged FRESH:
│       Fetch event count for last 24h (Crashlytics time-window filter)
│       Fetch event count for prior 7 days → compute daily average
│       If today_rate > 2 × 7day_avg → tag SPIKE=true
│     (Fresh issues skip spike detection — they are new by definition)
│
├─ Step 4: SessionHealthAnalyzer
│     GA4 Data API → fetch crashAffectedUsersRate + anrAffectedUsersRate
│       for last 30 days (daily granularity)
│     → Compute trend: IMPROVING / STABLE / DEGRADING
│     → If DEGRADING: rank issues by growth in affected users over same
│        period → identify top 3 drivers
│
├─ Step 5: IssuePrioritizer
│     Priority Score = affected_users × crash_rate
│                    × (1.5 if FRESH else 1.0)
│                    × (1.3 if SPIKE else 1.0)
│     → Assign tier: P0 (top 10%), P1 (next 30%), P2 (rest)
│
├─ Step 6: GitCorrelator  [FRESH issues only]
│     For each FRESH issue's stack trace:
│       git log -- <file_from_stack_trace> → find recent commits
│       GitHub REST API → find PR containing that commit
│     → Output per issue: PR title, author, merge date, URL
│
├─ Step 7: FixSuggester  [ALL issues]
│     Send stack trace + source file snippet → Gemini 1.5 Flash API
│     → Returns 2-3 sentence probable fix suggestion
│
└─ Step 8: ReportGenerator
      Combine all above → crash_report.html
      Deploy to GitHub Pages via gh-pages branch
```

---

## Free Services Used

| Service | Purpose | Free Tier |
|---|---|---|
| Firebase Crashlytics REST API | Fetch crash/ANR issues with time-window filters | Free (Spark plan + service account) |
| GA4 Data API | Crash-free / ANR-free session % trend | Free with Firebase-linked GA4 property |
| GitHub Actions | Scheduled pipeline runner | 2000 min/month (private), unlimited (public) |
| GitHub Pages | Host the HTML report | Free on all plans |
| GitHub REST API | PR & commit correlation (fresh issues only) | Free with personal access token |
| Gemini 1.5 Flash API | Fix suggestions via LLM (all issues) | 15 RPM, 1500 req/day — no credit card needed |

---

## Personal Account Setup Checklist

### Firebase (console.firebase.google.com)
- [ ] Create a new Firebase project (free Spark plan)
- [ ] Register a demo Android app in the project
- [ ] Enable Crashlytics for the app
- [ ] Go to Project Settings → Integrations → Google Analytics → note the **GA4 Property ID** (format: `123456789`)
- [ ] Go to Project Settings → Service Accounts → Generate new private key → download JSON
- [ ] Grant the service account the **Firebase Crashlytics Viewer** role and **Viewer** role on the GA4 property (Google Analytics → Admin → Property Access Management)
- [ ] Note down: `PROJECT_ID`, `APP_ID`, `GA4_PROPERTY_ID`

### Gemini API (aistudio.google.com)
- [ ] Sign in with Google account
- [ ] Create an API key (free, no credit card needed)
- [ ] Note down: `GEMINI_API_KEY`

### GitHub (personal account)
- [ ] Create a new repo: e.g., `crash-anr-agent`
- [ ] Enable GitHub Pages: Repo Settings → Pages → Source: `gh-pages` branch
- [ ] Add GitHub Actions secrets:
  - `FIREBASE_SERVICE_ACCOUNT` → paste full contents of Firebase service account JSON
  - `GEMINI_API_KEY` → Gemini API key
  - `GITHUB_TOKEN` → auto-provided by Actions, no setup needed
- [ ] Add repo variables:
  - `FIREBASE_PROJECT_ID`
  - `FIREBASE_APP_ID`
  - `GA4_PROPERTY_ID`
  - `GITHUB_REPO` → `your-username/demo-android-app` (for PR correlation)

---

## Demo Android App

A single-screen Kotlin app with buttons that deliberately trigger crashes and ANRs. The app is released as two versions to populate Crashlytics with data across both.

**v1.0 issues (existing — must NOT be tagged fresh in v1.1 report):**

| Button | Event type | What it does |
|---|---|---|
| "Trigger NPE" | CRASH | `val s: String? = null; s!!.length` |
| "Trigger IndexError" | CRASH | `listOf<Int>()[99]` |
| "Trigger ANR" | ANR | `Thread.sleep(8000)` on main thread |

**v1.1 issues (new — MUST be tagged FRESH in v1.1 report):**

| Button | Event type | What it does |
|---|---|---|
| "Trigger IllegalState" | CRASH | `check(false) { "PlayerManager failed" }` |
| "Trigger NetworkOnMain" | CRASH | `URL("http://example.com").readText()` on main thread |
| "Trigger ANR v2" | ANR | Nested `synchronized` deadlock on two objects |

**Population steps:**
1. Install v1.0 on emulator → tap each v1.0 button 3-4 times → let Crashlytics upload
2. Install v1.1 on same emulator → tap all buttons (both old and new) 3-4 times each → let Crashlytics upload
3. Confirm data appears in Firebase Crashlytics console before running the agent

---

## Report UI Design

**Visual language:** Firebase Console-inspired. White background (`#ffffff`), Roboto font, Google Blue (`#1a73e8`) as primary accent, card layout with `box-shadow: 0 1px 3px rgba(0,0,0,0.12)`, `border-radius: 8px`.

### Badge Color Coding

| Badge | Label | Color |
|---|---|---|
| Priority P0 | `P0` | Red `#d93025` |
| Priority P1 | `P1` | Orange `#f29900` |
| Priority P2 | `P2` | Gray `#5f6368` |
| Fresh | `🆕 NEW` | Green `#1e8e3e` |
| Spike | `⚡ SPIKE` | Purple `#a142f4` |
| Type: crash | `CRASH` | Blue `#1a73e8` |
| Type: ANR | `ANR` | Amber `#e37400` |

### Page Layout (top to bottom)

**1. Header bar**
- App icon placeholder (gray circle)
- Title: "Crash & ANR Report"
- Version range chip: `v1.0 → v1.1`
- Report date (right-aligned)

**2. Summary stat cards (row of 4)**
- Total Issues · Fresh Issues · P0 Count · Spiking Issues

**3. Session Health card**
- Crash-free sessions %: today's value + 30-day sparkline + trend arrow (↑ / → / ↓)
- ANR-free sessions %: same treatment
- If trend is DEGRADING: "Top drivers of decline" — list of up to 3 issues ranked by growth in affected users, each as a chip linking to that issue's row in the table below

**4. Filter bar**
- Type: All / CRASH / ANR
- Priority: All / P0 / P1 / P2
- Status: All / Fresh / Spiking / Existing

**5. Issue table**

Each row contains:
- Priority badge + Type badge + Fresh badge (if applicable) + Spike badge (if applicable)
- Exception type + top frame (e.g. `IllegalStateException in PlayerManager.kt:42`)
- Affected users count
- First seen version

Each row is expandable (click to reveal):
- **Stack trace panel** — monospace font, scrollable, max-height 300px
- **Fix suggestion panel** — Gemini's 2-3 sentence suggestion in an italicized card
- **PR list panel** *(fresh issues only)* — each linked PR as a chip: title · author · merge date · clickable URL

---

## GitHub Actions Workflow

```yaml
# .github/workflows/crash-report.yml
name: Crash & ANR Report
on:
  schedule:
    - cron: '0 9 * * *'   # Daily at 9 AM UTC
  workflow_dispatch:        # Manual trigger for demos

jobs:
  generate-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: python agent/main.py
        env:
          FIREBASE_SERVICE_ACCOUNT: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          FIREBASE_PROJECT_ID: ${{ vars.FIREBASE_PROJECT_ID }}
          FIREBASE_APP_ID: ${{ vars.FIREBASE_APP_ID }}
          GA4_PROPERTY_ID: ${{ vars.GA4_PROPERTY_ID }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPO: ${{ vars.GITHUB_REPO }}
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
```

---

## Project File Structure

```
crash-anr-agent/
├── .github/
│   └── workflows/
│       └── crash-report.yml
├── agent/
│   ├── main.py                    # Orchestrator — runs all steps in order
│   ├── crash_fetcher.py           # Firebase Crashlytics REST API client
│   ├── fresh_detector.py          # Compares signatures across versions
│   ├── spike_detector.py          # Time-window rate comparison for spike detection
│   ├── session_health_analyzer.py # GA4 Data API — crash-free/ANR-free trend
│   ├── prioritizer.py             # Scoring + P0/P1/P2 assignment
│   ├── git_correlator.py          # git log + GitHub API for PR lookup (fresh only)
│   ├── fix_suggester.py           # Gemini API client (all issues)
│   └── report_generator.py        # Renders crash_report.html from template
├── templates/
│   └── report.html.jinja          # Jinja2 HTML report template
├── output/                        # Generated report (gitignored)
│   └── crash_report.html
├── requirements.txt
└── README.md
```

---

## Firebase Crashlytics API Notes

- **Base URL:** `https://crashlytics.googleapis.com/v1alpha`
- **Auth:** OAuth2 via service account JSON — scope: `https://www.googleapis.com/auth/cloud-platform`
- **List issues endpoint:** `GET /projects/{projectId}/apps/{appId}/issues`
  - Filter by version: `filter=appVersion="{versionName}"`
  - Filter by time window: `filter=lastSeenTime>"{ISO8601}"` (for spike detection)
- **GA4 Data API base URL:** `https://analyticsdata.googleapis.com/v1beta`
- **GA4 report endpoint:** `POST /properties/{propertyId}:runReport`
  - Additional service account scope: `https://www.googleapis.com/auth/analytics.readonly`
  - Metrics: `crashAffectedUsersRate`, `anrAffectedUsersRate`
  - Date range: last 30 days, daily granularity

> **Note:** Exact Crashlytics filter syntax should be verified against the API Explorer during implementation. The v1alpha API is the current documented version as of this design.

---

## What's Pending (implementation)

- [ ] Create personal GitHub repo `crash-anr-agent`
- [ ] Complete Firebase + GA4 setup (checklist above)
- [ ] Build and test each pipeline step
- [ ] Build and populate demo Android app with v1.0 and v1.1 crash/ANR data
- [ ] End-to-end run with demo app data
- [ ] Polish report for pitch to Pocket FM team
