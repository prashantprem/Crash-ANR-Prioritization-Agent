# Crash & ANR Prioritization Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily-scheduled Python agent that fetches crash/ANR data from Firebase Crashlytics, detects fresh issues and spikes, tracks session health via GA4, correlates fresh issues to GitHub PRs, generates Gemini fix suggestions, and publishes a Firebase Console-styled HTML report to GitHub Pages.

**Architecture:** Monorepo — Android demo app (`app/`) populates Crashlytics with test data; Python pipeline (`agent/`) runs as a GitHub Actions scheduled job and deploys the report. Each pipeline step is an independent module that enriches a shared `Issue` dataclass.

**Tech Stack:** Python 3.12, pytest, google-auth, requests, google-analytics-data, google-generativeai, Jinja2, Firebase Crashlytics REST API (v1alpha), GA4 Data API, Gemini 1.5 Flash, GitHub REST API, Kotlin + Jetpack Compose + Firebase Crashlytics SDK.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Create | Python dependencies |
| `pytest.ini` | Create | Pytest config |
| `agent/__init__.py` | Create | Package marker |
| `agent/models.py` | Create | Issue, LinkedPR, SessionHealth dataclasses |
| `agent/auth.py` | Create | Service account → access token |
| `agent/crash_fetcher.py` | Create | Crashlytics REST API — fetch issues by version |
| `agent/fresh_detector.py` | Create | Tag issues absent in previous version |
| `agent/spike_detector.py` | Create | Tag issues with 2× daily rate spike |
| `agent/session_health_analyzer.py` | Create | GA4 crash-free/ANR-free trend |
| `agent/prioritizer.py` | Create | Score + assign P0/P1/P2 tier |
| `agent/git_correlator.py` | Create | GitHub API PR lookup (FRESH issues only) |
| `agent/fix_suggester.py` | Create | Gemini 1.5 Flash fix suggestions (all issues) |
| `agent/report_generator.py` | Create | Render Jinja2 → HTML |
| `agent/main.py` | Create | Orchestrator — run all steps in order |
| `templates/report.html.jinja` | Create | Firebase Console-styled HTML report |
| `tests/__init__.py` | Create | Package marker |
| `tests/conftest.py` | Create | Shared test fixtures |
| `tests/test_crash_fetcher.py` | Create | CrashFetcher unit tests |
| `tests/test_fresh_detector.py` | Create | FreshIssueDetector unit tests |
| `tests/test_spike_detector.py` | Create | SpikeDetector unit tests |
| `tests/test_session_health_analyzer.py` | Create | SessionHealthAnalyzer unit tests |
| `tests/test_prioritizer.py` | Create | IssuePrioritizer unit tests |
| `tests/test_git_correlator.py` | Create | GitCorrelator unit tests |
| `tests/test_fix_suggester.py` | Create | FixSuggester unit tests |
| `tests/test_report_generator.py` | Create | ReportGenerator unit tests |
| `build.gradle.kts` | Modify | Add google-services + crashlytics plugins |
| `app/build.gradle.kts` | Modify | Apply plugins, add Firebase dependencies |
| `app/src/main/AndroidManifest.xml` | Modify | Add INTERNET permission |
| `app/src/main/java/com/example/crashdemo/MainActivity.kt` | Replace | Crash/ANR trigger UI |
| `.github/workflows/crash-report.yml` | Create | Scheduled pipeline + GitHub Pages deploy |

---

## Task 0: Python project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `agent/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
google-auth==2.29.0
google-auth-httplib2==0.2.0
requests==2.32.3
google-analytics-data==0.18.9
google-generativeai==0.7.2
jinja2==3.1.4
pytest==8.2.2
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 3: Create `agent/__init__.py` and `tests/__init__.py`**

Both files are empty. Run:
```bash
touch agent/__init__.py tests/__init__.py
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import pytest
from agent.models import Issue


@pytest.fixture
def make_issue():
    def _make(
        id="test-1",
        issue_type="CRASH",
        event_count=10,
        user_count=5,
        is_fresh=False,
        is_spike=False,
        stack_trace="at com.example.crashdemo.PlayerManager.start(PlayerManager.kt:42)",
        title="IllegalStateException in PlayerManager.kt:42",
        first_seen_version="1.1",
    ):
        issue = Issue(
            id=id,
            issue_type=issue_type,
            title=title,
            event_count=event_count,
            user_count=user_count,
            first_seen_version=first_seen_version,
            last_seen_time="2026-04-10T09:00:00Z",
            stack_trace=stack_trace,
        )
        issue.is_fresh = is_fresh
        issue.is_spike = is_spike
        return issue

    return _make
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini agent/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: python project scaffold — dependencies and test config"
```

---

## Task 1: Data models

**Files:**
- Create: `agent/models.py`

- [ ] **Step 1: Create `agent/models.py`**

```python
from dataclasses import dataclass, field


@dataclass
class LinkedPR:
    title: str
    author: str
    merge_date: str
    url: str


@dataclass
class Issue:
    id: str
    issue_type: str          # "CRASH" or "ANR"
    title: str
    event_count: int
    user_count: int
    first_seen_version: str
    last_seen_time: str      # ISO 8601 string
    stack_trace: str
    is_fresh: bool = False
    is_spike: bool = False
    priority_score: float = 0.0
    priority_tier: str = ""  # "P0", "P1", or "P2"
    linked_prs: list = field(default_factory=list)
    fix_suggestion: str = ""


@dataclass
class SessionHealth:
    crash_free_rate_today: float
    anr_free_rate_today: float
    trend: str               # "IMPROVING", "STABLE", or "DEGRADING"
    driving_issue_ids: list = field(default_factory=list)
    daily_crash_free: list = field(default_factory=list)
    daily_anr_free: list = field(default_factory=list)
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from agent.models import Issue, LinkedPR, SessionHealth; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add agent/models.py
git commit -m "feat: add Issue, LinkedPR, SessionHealth dataclasses"
```

---

## Task 2: Firebase auth helper

**Files:**
- Create: `agent/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from agent.auth import get_access_token


FAKE_SA = json.dumps({
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id",
    "private_key": "fake-key",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
})


def test_get_access_token_returns_string():
    mock_creds = MagicMock()
    mock_creds.token = "ya29.fake-token"

    with patch("agent.auth.service_account.Credentials.from_service_account_info",
               return_value=mock_creds), \
         patch("agent.auth.google.auth.transport.requests.Request"), \
         patch.object(mock_creds, "refresh"):
        token = get_access_token(FAKE_SA)

    assert token == "ya29.fake-token"


def test_get_access_token_uses_correct_scopes():
    mock_creds = MagicMock()
    mock_creds.token = "ya29.fake"

    with patch("agent.auth.service_account.Credentials.from_service_account_info",
               return_value=mock_creds) as mock_from_info, \
         patch("agent.auth.google.auth.transport.requests.Request"), \
         patch.object(mock_creds, "refresh"):
        get_access_token(FAKE_SA)

    _, kwargs = mock_from_info.call_args
    assert "https://www.googleapis.com/auth/cloud-platform" in kwargs["scopes"]
    assert "https://www.googleapis.com/auth/analytics.readonly" in kwargs["scopes"]
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `agent.auth` does not exist yet.

- [ ] **Step 3: Create `agent/auth.py`**

```python
import json

import google.auth.transport.requests
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def get_access_token(service_account_json: str) -> str:
    info = json.loads(service_account_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/auth.py tests/test_auth.py
git commit -m "feat: add Firebase service account auth helper"
```

---

## Task 3: CrashFetcher

**Files:**
- Create: `agent/crash_fetcher.py`
- Create: `tests/test_crash_fetcher.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_crash_fetcher.py`:

```python
from unittest.mock import patch, MagicMock
from agent.crash_fetcher import fetch_issues

FAKE_RESPONSE = {
    "issues": [
        {
            "name": "projects/proj/apps/app/issues/abc123",
            "type": "CRASH",
            "title": "NullPointerException in HomeViewModel.kt:55",
            "eventCount": "42",
            "userCount": "10",
            "appVersion": "1.1",
            "lastSeenTime": "2026-04-10T08:00:00Z",
            "representativeEvent": {
                "exceptionInfo": {
                    "stackTrace": "at com.example.HomeViewModel.load(HomeViewModel.kt:55)"
                }
            },
        },
        {
            "name": "projects/proj/apps/app/issues/def456",
            "type": "ANR",
            "title": "ANR in MainActivity",
            "eventCount": "5",
            "userCount": "3",
            "appVersion": "1.1",
            "lastSeenTime": "2026-04-10T07:00:00Z",
            "representativeEvent": {"exceptionInfo": {"stackTrace": ""}},
        },
    ]
}


def test_fetch_issues_returns_issue_list():
    mock_resp = MagicMock()
    mock_resp.json.return_value = FAKE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("agent.crash_fetcher.requests.get", return_value=mock_resp):
        issues = fetch_issues("fake-token", "proj", "app", "1.1")

    assert len(issues) == 2


def test_fetch_issues_parses_fields_correctly():
    mock_resp = MagicMock()
    mock_resp.json.return_value = FAKE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("agent.crash_fetcher.requests.get", return_value=mock_resp):
        issues = fetch_issues("fake-token", "proj", "app", "1.1")

    crash = issues[0]
    assert crash.id == "abc123"
    assert crash.issue_type == "CRASH"
    assert crash.event_count == 42
    assert crash.user_count == 10
    assert "HomeViewModel" in crash.stack_trace

    anr = issues[1]
    assert anr.issue_type == "ANR"


def test_fetch_issues_handles_pagination():
    page1 = {"issues": [FAKE_RESPONSE["issues"][0]], "nextPageToken": "tok"}
    page2 = {"issues": [FAKE_RESPONSE["issues"][1]]}

    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = page1
    mock_resp1.raise_for_status = MagicMock()

    mock_resp2 = MagicMock()
    mock_resp2.json.return_value = page2
    mock_resp2.raise_for_status = MagicMock()

    with patch("agent.crash_fetcher.requests.get", side_effect=[mock_resp1, mock_resp2]):
        issues = fetch_issues("fake-token", "proj", "app", "1.1")

    assert len(issues) == 2
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_crash_fetcher.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/crash_fetcher.py`**

```python
import requests

from .models import Issue

CRASHLYTICS_BASE = "https://crashlytics.googleapis.com/v1alpha"


def fetch_issues(
    token: str, project_id: str, app_id: str, version: str
) -> list[Issue]:
    url = f"{CRASHLYTICS_BASE}/projects/{project_id}/apps/{app_id}/issues"
    headers = {"Authorization": f"Bearer {token}"}
    issues = []
    page_token = None

    while True:
        params: dict = {
            "filter": f'appVersion="{version}"',
            "pageSize": 100,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("issues", []):
            issues.append(_parse_issue(item))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return issues


def _parse_issue(item: dict) -> Issue:
    # Field names verified against Crashlytics v1alpha API.
    # If fields differ in the live API, adjust the key names here.
    return Issue(
        id=item["name"].split("/")[-1],
        issue_type=item.get("type", "CRASH"),
        title=item.get("title", "Unknown"),
        event_count=int(item.get("eventCount", 0)),
        user_count=int(item.get("userCount", 0)),
        first_seen_version=item.get("appVersion", ""),
        last_seen_time=item.get("lastSeenTime", ""),
        stack_trace=(
            item.get("representativeEvent", {})
            .get("exceptionInfo", {})
            .get("stackTrace", "")
        ),
    )
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_crash_fetcher.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/crash_fetcher.py tests/test_crash_fetcher.py
git commit -m "feat: add CrashFetcher — Crashlytics REST API client"
```

---

## Task 4: FreshIssueDetector

**Files:**
- Create: `agent/fresh_detector.py`
- Create: `tests/test_fresh_detector.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fresh_detector.py`:

```python
from agent.fresh_detector import detect_fresh
from agent.models import Issue


def _issue(id: str) -> Issue:
    return Issue(
        id=id, issue_type="CRASH", title="Test", event_count=10,
        user_count=5, first_seen_version="1.1",
        last_seen_time="2026-04-10T09:00:00Z", stack_trace="",
    )


def test_marks_issues_absent_in_previous_as_fresh():
    current = [_issue("A"), _issue("B"), _issue("C")]
    previous = [_issue("A")]
    result = detect_fresh(current, previous)
    assert result[0].is_fresh is False  # A was in previous
    assert result[1].is_fresh is True   # B is new
    assert result[2].is_fresh is True   # C is new


def test_no_fresh_when_all_issues_match():
    current = [_issue("A"), _issue("B")]
    previous = [_issue("A"), _issue("B")]
    result = detect_fresh(current, previous)
    assert all(not i.is_fresh for i in result)


def test_all_fresh_when_previous_is_empty():
    current = [_issue("X"), _issue("Y")]
    result = detect_fresh(current, [])
    assert all(i.is_fresh for i in result)


def test_returns_same_list_mutated_in_place():
    current = [_issue("A")]
    result = detect_fresh(current, [])
    assert result is current
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_fresh_detector.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/fresh_detector.py`**

```python
from .models import Issue


def detect_fresh(
    current_issues: list[Issue], previous_issues: list[Issue]
) -> list[Issue]:
    previous_ids = {issue.id for issue in previous_issues}
    for issue in current_issues:
        issue.is_fresh = issue.id not in previous_ids
    return current_issues
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_fresh_detector.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/fresh_detector.py tests/test_fresh_detector.py
git commit -m "feat: add FreshIssueDetector — tag issues absent in previous version"
```

---

## Task 5: SpikeDetector

**Files:**
- Create: `agent/spike_detector.py`
- Create: `tests/test_spike_detector.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_spike_detector.py`:

```python
from unittest.mock import patch, MagicMock
from agent.spike_detector import detect_spikes
from agent.models import Issue


def _issue(id: str, is_fresh: bool = False) -> Issue:
    i = Issue(
        id=id, issue_type="CRASH", title="Test", event_count=10,
        user_count=5, first_seen_version="1.1",
        last_seen_time="2026-04-10T09:00:00Z", stack_trace="",
    )
    i.is_fresh = is_fresh
    return i


def _mock_fetch(today_counts: dict, seven_day_counts: dict):
    """Returns a side_effect list: first call = 7-day, second call = 1-day."""
    def side_effect(token, project_id, app_id, version, since):
        # spike_detector calls 7-day first, then 1-day
        if "7_day" in since or side_effect.call_count == 0:
            side_effect.call_count += 1
            return seven_day_counts
        side_effect.call_count += 1
        return today_counts
    side_effect.call_count = 0
    return side_effect


def test_flags_issue_as_spike_when_today_exceeds_twice_weekly_avg():
    issues = [_issue("A")]

    with patch("agent.spike_detector._fetch_counts_since") as mock_fetch:
        # 7-day total = 7, daily avg = 1; today = 3 → 3 > 2×1 → SPIKE
        mock_fetch.side_effect = [{"A": 7}, {"A": 3}]
        result = detect_spikes(issues, "tok", "proj", "app", "1.1")

    assert result[0].is_spike is True


def test_does_not_flag_when_today_within_normal_range():
    issues = [_issue("A")]

    with patch("agent.spike_detector._fetch_counts_since") as mock_fetch:
        # 7-day total = 70, daily avg = 10; today = 12 → 12 < 2×10 → no spike
        mock_fetch.side_effect = [{"A": 70}, {"A": 12}]
        result = detect_spikes(issues, "tok", "proj", "app", "1.1")

    assert result[0].is_spike is False


def test_fresh_issues_skip_spike_detection():
    issues = [_issue("A", is_fresh=True)]

    with patch("agent.spike_detector._fetch_counts_since") as mock_fetch:
        result = detect_spikes(issues, "tok", "proj", "app", "1.1")

    mock_fetch.assert_not_called()
    assert result[0].is_spike is False


def test_no_spike_when_weekly_avg_is_zero():
    issues = [_issue("A")]

    with patch("agent.spike_detector._fetch_counts_since") as mock_fetch:
        mock_fetch.side_effect = [{"A": 0}, {"A": 5}]
        result = detect_spikes(issues, "tok", "proj", "app", "1.1")

    assert result[0].is_spike is False
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_spike_detector.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/spike_detector.py`**

```python
from datetime import datetime, timedelta, timezone

import requests

from .models import Issue

CRASHLYTICS_BASE = "https://crashlytics.googleapis.com/v1alpha"


def detect_spikes(
    issues: list[Issue],
    token: str,
    project_id: str,
    app_id: str,
    version: str,
) -> list[Issue]:
    now = datetime.now(timezone.utc)
    one_day_ago = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    seven_day_counts = _fetch_counts_since(
        token, project_id, app_id, version, seven_days_ago
    )
    today_counts = _fetch_counts_since(
        token, project_id, app_id, version, one_day_ago
    )

    for issue in issues:
        if issue.is_fresh:
            continue

        today = today_counts.get(issue.id, 0)
        weekly_avg = seven_day_counts.get(issue.id, 0) / 7

        if weekly_avg > 0 and today > 2 * weekly_avg:
            issue.is_spike = True

    return issues


def _fetch_counts_since(
    token: str, project_id: str, app_id: str, version: str, since: str
) -> dict[str, int]:
    # Crashlytics v1alpha filter syntax — verify against API Explorer if needed.
    # "lastSeenTime" filters issues active within the time window.
    url = f"{CRASHLYTICS_BASE}/projects/{project_id}/apps/{app_id}/issues"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": f'appVersion="{version}" AND lastSeenTime>"{since}"',
        "pageSize": 100,
    }
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    return {
        item["name"].split("/")[-1]: int(item.get("eventCount", 0))
        for item in data.get("issues", [])
    }
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_spike_detector.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/spike_detector.py tests/test_spike_detector.py
git commit -m "feat: add SpikeDetector — flag issues with 2× daily rate increase"
```

---

## Task 6: SessionHealthAnalyzer

**Files:**
- Create: `agent/session_health_analyzer.py`
- Create: `tests/test_session_health_analyzer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_session_health_analyzer.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agent.session_health_analyzer import _compute_trend, _find_drivers, analyze_session_health
from agent.models import Issue, SessionHealth


def _issue(id: str, user_count: int) -> Issue:
    i = Issue(
        id=id, issue_type="CRASH", title="T", event_count=10,
        user_count=user_count, first_seen_version="1.1",
        last_seen_time="", stack_trace="",
    )
    return i


def test_compute_trend_returns_degrading_when_recent_worse():
    # Recent 3 days ~0.90, older 7 days ~0.97 → delta = -0.07 → DEGRADING
    rates = [0.97] * 7 + [0.90, 0.90, 0.90]
    assert _compute_trend(rates) == "DEGRADING"


def test_compute_trend_returns_improving_when_recent_better():
    # Recent 3 days ~0.99, older 7 days ~0.92 → delta = +0.07 → IMPROVING
    rates = [0.92] * 7 + [0.99, 0.99, 0.99]
    assert _compute_trend(rates) == "IMPROVING"


def test_compute_trend_returns_stable_when_delta_small():
    rates = [0.95] * 10
    assert _compute_trend(rates) == "STABLE"


def test_compute_trend_returns_stable_when_insufficient_data():
    assert _compute_trend([0.90, 0.80]) == "STABLE"


def test_find_drivers_returns_empty_when_not_degrading():
    issues = [_issue("A", 10), _issue("B", 5)]
    assert _find_drivers(issues, "STABLE") == []
    assert _find_drivers(issues, "IMPROVING") == []


def test_find_drivers_returns_top_3_by_user_count():
    issues = [
        _issue("A", 5), _issue("B", 100), _issue("C", 50), _issue("D", 200)
    ]
    drivers = _find_drivers(issues, "DEGRADING")
    assert drivers == ["D", "B", "C"]


def test_analyze_session_health_returns_session_health():
    mock_row = MagicMock()
    mock_row.metric_values = [MagicMock(value="0.05"), MagicMock(value="0.01")]

    mock_response = MagicMock()
    mock_response.rows = [mock_row] * 10

    sa_info = {"type": "service_account"}

    with patch("agent.session_health_analyzer.service_account.Credentials.from_service_account_info"), \
         patch("agent.session_health_analyzer.BetaAnalyticsDataClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.run_report.return_value = mock_response
        result = analyze_session_health(sa_info, "12345", [])

    assert isinstance(result, SessionHealth)
    assert result.crash_free_rate_today == pytest.approx(0.95)
    assert result.trend in ("IMPROVING", "STABLE", "DEGRADING")
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_session_health_analyzer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/session_health_analyzer.py`**

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

from .models import Issue, SessionHealth

# GA4 metric names for Firebase Crashlytics integration.
# If "crashAffectedUsersRate" is not available in your GA4 property,
# check available metrics via:
#   GET https://analyticsdata.googleapis.com/v1beta/properties/{id}/metadata
CRASH_METRIC = "crashAffectedUsersRate"
ANR_METRIC = "anrAffectedUsersRate"


def analyze_session_health(
    service_account_info: dict,
    property_id: str,
    issues: list[Issue],
) -> SessionHealth:
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name=CRASH_METRIC), Metric(name=ANR_METRIC)],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
    )

    response = client.run_report(request)

    daily_crash_free = []
    daily_anr_free = []

    for row in response.rows:
        crash_rate = float(row.metric_values[0].value or 0)
        anr_rate = float(row.metric_values[1].value or 0)
        daily_crash_free.append(1.0 - crash_rate)
        daily_anr_free.append(1.0 - anr_rate)

    trend = _compute_trend(daily_crash_free)
    driving_ids = _find_drivers(issues, trend)

    return SessionHealth(
        crash_free_rate_today=daily_crash_free[-1] if daily_crash_free else 1.0,
        anr_free_rate_today=daily_anr_free[-1] if daily_anr_free else 1.0,
        trend=trend,
        driving_issue_ids=driving_ids,
        daily_crash_free=daily_crash_free,
        daily_anr_free=daily_anr_free,
    )


def _compute_trend(daily_rates: list[float]) -> str:
    if len(daily_rates) < 7:
        return "STABLE"
    recent = sum(daily_rates[-3:]) / 3
    older = sum(daily_rates[-10:-3]) / 7
    delta = recent - older
    if delta > 0.005:
        return "IMPROVING"
    if delta < -0.005:
        return "DEGRADING"
    return "STABLE"


def _find_drivers(issues: list[Issue], trend: str) -> list[str]:
    if trend != "DEGRADING":
        return []
    sorted_issues = sorted(issues, key=lambda i: i.user_count, reverse=True)
    return [i.id for i in sorted_issues[:3]]
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_session_health_analyzer.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/session_health_analyzer.py tests/test_session_health_analyzer.py
git commit -m "feat: add SessionHealthAnalyzer — GA4 crash-free/ANR-free trend"
```

---

## Task 7: IssuePrioritizer

**Files:**
- Create: `agent/prioritizer.py`
- Create: `tests/test_prioritizer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_prioritizer.py`:

```python
from agent.prioritizer import prioritize
from agent.models import Issue


def _issue(id, user_count, event_count, is_fresh=False, is_spike=False):
    i = Issue(
        id=id, issue_type="CRASH", title="", event_count=event_count,
        user_count=user_count, first_seen_version="1.1",
        last_seen_time="", stack_trace="",
    )
    i.is_fresh = is_fresh
    i.is_spike = is_spike
    return i


def test_fresh_multiplier_boosts_score_above_non_fresh():
    base = _issue("A", user_count=100, event_count=10)
    fresh = _issue("B", user_count=100, event_count=10, is_fresh=True)
    result = prioritize([base, fresh])
    scores = {i.id: i.priority_score for i in result}
    assert scores["B"] > scores["A"]


def test_spike_multiplier_boosts_score_above_non_spike():
    base = _issue("A", user_count=100, event_count=10)
    spike = _issue("B", user_count=100, event_count=10, is_spike=True)
    result = prioritize([base, spike])
    scores = {i.id: i.priority_score for i in result}
    assert scores["B"] > scores["A"]


def test_p0_assigned_to_top_10_percent():
    issues = [_issue(str(i), user_count=100 - i, event_count=10) for i in range(10)]
    result = prioritize(issues)
    p0 = [i for i in result if i.priority_tier == "P0"]
    assert len(p0) == 1


def test_result_sorted_descending_by_priority_score():
    issues = [
        _issue("low", user_count=1, event_count=1),
        _issue("high", user_count=1000, event_count=100),
    ]
    result = prioritize(issues)
    assert result[0].id == "high"
    assert result[1].id == "low"


def test_single_issue_gets_p0():
    issues = [_issue("A", user_count=50, event_count=5)]
    result = prioritize(issues)
    assert result[0].priority_tier == "P0"


def test_all_issues_get_a_tier():
    issues = [_issue(str(i), user_count=i + 1, event_count=1) for i in range(20)]
    result = prioritize(issues)
    assert all(i.priority_tier in ("P0", "P1", "P2") for i in result)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_prioritizer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/prioritizer.py`**

```python
from .models import Issue


def prioritize(issues: list[Issue]) -> list[Issue]:
    for issue in issues:
        base = issue.user_count * max(issue.event_count, 1)
        fresh_mult = 1.5 if issue.is_fresh else 1.0
        spike_mult = 1.3 if issue.is_spike else 1.0
        issue.priority_score = base * fresh_mult * spike_mult

    issues.sort(key=lambda i: i.priority_score, reverse=True)
    n = len(issues)
    p0_cutoff = max(1, round(n * 0.10))
    p1_cutoff = max(1, round(n * 0.40))

    for idx, issue in enumerate(issues):
        if idx < p0_cutoff:
            issue.priority_tier = "P0"
        elif idx < p1_cutoff:
            issue.priority_tier = "P1"
        else:
            issue.priority_tier = "P2"

    return issues
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_prioritizer.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/prioritizer.py tests/test_prioritizer.py
git commit -m "feat: add IssuePrioritizer — score and assign P0/P1/P2 tiers"
```

---

## Task 8: GitCorrelator

**Files:**
- Create: `agent/git_correlator.py`
- Create: `tests/test_git_correlator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_git_correlator.py`:

```python
from unittest.mock import patch, MagicMock
from agent.git_correlator import correlate, _extract_files, _get_pr_for_commit
from agent.models import Issue, LinkedPR


def _fresh_issue(stack_trace: str) -> Issue:
    i = Issue(
        id="issue-1", issue_type="CRASH", title="Test", event_count=5,
        user_count=2, first_seen_version="1.1", last_seen_time="", stack_trace=stack_trace,
    )
    i.is_fresh = True
    return i


def _non_fresh_issue() -> Issue:
    return Issue(
        id="issue-2", issue_type="CRASH", title="Old", event_count=1,
        user_count=1, first_seen_version="1.0", last_seen_time="", stack_trace="",
    )


def test_extract_files_from_stack_trace():
    stack = (
        "at com.example.crashdemo.PlayerManager.start(PlayerManager.kt:42)\n"
        "at com.example.crashdemo.MainActivity.onCreate(MainActivity.kt:20)"
    )
    files = _extract_files(stack)
    assert "com/example/crashdemo/PlayerManager.kt" in files
    assert "com/example/crashdemo/MainActivity.kt" in files


def test_extract_files_deduplicates():
    stack = (
        "at com.example.Foo.bar(Foo.kt:1)\n"
        "at com.example.Foo.baz(Foo.kt:2)"
    )
    files = _extract_files(stack)
    assert files.count("com/example/Foo.kt") == 1


def test_non_fresh_issues_skipped():
    issues = [_non_fresh_issue()]
    with patch("agent.git_correlator.requests.get") as mock_get:
        result = correlate(issues, "tok", "owner/repo")
    mock_get.assert_not_called()
    assert result[0].linked_prs == []


def test_fresh_issue_gets_pr_linked():
    stack = "at com.example.crashdemo.PlayerManager.start(PlayerManager.kt:42)"
    issue = _fresh_issue(stack)

    commit_resp = MagicMock()
    commit_resp.status_code = 200
    commit_resp.json.return_value = [{"sha": "abc123"}]

    pr_resp = MagicMock()
    pr_resp.status_code = 200
    pr_resp.json.return_value = [{
        "title": "Add player", "user": {"login": "devA"},
        "merged_at": "2026-04-01T12:00:00Z", "html_url": "https://github.com/owner/repo/pull/5"
    }]

    with patch("agent.git_correlator.requests.get", side_effect=[commit_resp, pr_resp]):
        result = correlate([issue], "tok", "owner/repo")

    assert len(result[0].linked_prs) == 1
    pr = result[0].linked_prs[0]
    assert pr.title == "Add player"
    assert pr.author == "devA"
    assert pr.merge_date == "2026-04-01"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_git_correlator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/git_correlator.py`**

```python
import re

import requests

from .models import Issue, LinkedPR

GITHUB_API = "https://api.github.com"


def correlate(issues: list[Issue], token: str, repo: str) -> list[Issue]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for issue in issues:
        if not issue.is_fresh:
            continue
        files = _extract_files(issue.stack_trace)
        prs: list[LinkedPR] = []
        seen_urls: set[str] = set()
        for file_path in files[:3]:
            for sha in _get_recent_commits(headers, repo, file_path):
                pr = _get_pr_for_commit(headers, repo, sha)
                if pr and pr.url not in seen_urls:
                    seen_urls.add(pr.url)
                    prs.append(pr)
        issue.linked_prs = prs[:5]
    return issues


def _extract_files(stack_trace: str) -> list[str]:
    pattern = r"at ([\w.]+)\((\w+\.kt):\d+\)"
    seen: set[str] = set()
    files: list[str] = []
    for pkg_method, filename in re.findall(pattern, stack_trace):
        parts = pkg_method.rsplit(".", 1)
        if len(parts) == 2:
            path = f"{parts[0].replace('.', '/')}/{filename}"
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _get_recent_commits(headers: dict, repo: str, file_path: str) -> list[str]:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/commits",
        headers=headers,
        params={"path": file_path, "per_page": 5},
    )
    if resp.status_code != 200:
        return []
    return [c["sha"] for c in resp.json()]


def _get_pr_for_commit(headers: dict, repo: str, sha: str) -> LinkedPR | None:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/commits/{sha}/pulls",
        headers=headers,
    )
    if resp.status_code != 200 or not resp.json():
        return None
    pr = resp.json()[0]
    merged_at = pr.get("merged_at") or ""
    return LinkedPR(
        title=pr["title"],
        author=pr["user"]["login"],
        merge_date=merged_at[:10],
        url=pr["html_url"],
    )
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_git_correlator.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/git_correlator.py tests/test_git_correlator.py
git commit -m "feat: add GitCorrelator — GitHub PR lookup for fresh issues"
```

---

## Task 9: FixSuggester

**Files:**
- Create: `agent/fix_suggester.py`
- Create: `tests/test_fix_suggester.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fix_suggester.py`:

```python
from unittest.mock import patch, MagicMock
from agent.fix_suggester import suggest_fixes
from agent.models import Issue


def _issue(id: str, stack_trace: str = "at com.example.Foo.bar(Foo.kt:1)") -> Issue:
    return Issue(
        id=id, issue_type="CRASH", title="Test", event_count=1,
        user_count=1, first_seen_version="1.1", last_seen_time="", stack_trace=stack_trace,
    )


def test_suggest_fixes_populates_fix_suggestion_for_all_issues():
    issues = [_issue("A"), _issue("B")]
    mock_response = MagicMock()
    mock_response.text = "Check for null before accessing the field."

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.return_value = mock_response
        result = suggest_fixes(issues, "fake-api-key")

    assert result[0].fix_suggestion == "Check for null before accessing the field."
    assert result[1].fix_suggestion == "Check for null before accessing the field."


def test_suggest_fixes_handles_api_error_gracefully():
    issues = [_issue("A")]

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.side_effect = Exception("API quota exceeded")
        result = suggest_fixes(issues, "fake-key")

    assert result[0].fix_suggestion == "Unable to generate suggestion."


def test_suggest_fixes_sends_stack_trace_in_prompt():
    issues = [_issue("A", stack_trace="at com.example.Foo.crash(Foo.kt:99)")]
    mock_response = MagicMock()
    mock_response.text = "Fix it."

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.return_value = mock_response
        suggest_fixes(issues, "key")

    prompt = mock_model.generate_content.call_args[0][0]
    assert "Foo.kt:99" in prompt
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_fix_suggester.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/fix_suggester.py`**

```python
import google.generativeai as genai

from .models import Issue


def suggest_fixes(issues: list[Issue], api_key: str) -> list[Issue]:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    for issue in issues:
        prompt = (
            "This Android app crashed with the following stack trace:\n\n"
            f"{issue.stack_trace}\n\n"
            "In 2-3 sentences, suggest the most likely cause and fix."
        )
        try:
            response = model.generate_content(prompt)
            issue.fix_suggestion = response.text.strip()
        except Exception:
            issue.fix_suggestion = "Unable to generate suggestion."

    return issues
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_fix_suggester.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/fix_suggester.py tests/test_fix_suggester.py
git commit -m "feat: add FixSuggester — Gemini 1.5 Flash fix suggestions for all issues"
```

---

## Task 10: HTML report template

**Files:**
- Create: `templates/report.html.jinja`

No unit test for the template — it's validated visually in Task 11.

- [ ] **Step 1: Create `templates/` directory**

```bash
mkdir -p templates
```

- [ ] **Step 2: Create `templates/report.html.jinja`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Crash &amp; ANR Report — {{ report_date }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Roboto', sans-serif; background: #f5f5f5; color: #202124; font-size: 14px; }

    /* Header */
    .header { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 0 24px; height: 64px; display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 10; }
    .header-logo { width: 28px; height: 28px; }
    .header h1 { font-size: 20px; font-weight: 500; color: #202124; }
    .version-chip { background: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }
    .report-date { margin-left: auto; color: #5f6368; font-size: 13px; }

    /* Container */
    .container { max-width: 1200px; margin: 24px auto; padding: 0 24px; display: flex; flex-direction: column; gap: 20px; }

    /* Cards */
    .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08); }

    /* Stat cards */
    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    .stat-card { padding: 20px 24px; }
    .stat-label { font-size: 12px; color: #5f6368; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 36px; font-weight: 400; }

    /* Session health */
    .health-card { padding: 20px 24px; }
    .health-card h2 { font-size: 16px; font-weight: 500; margin-bottom: 4px; }
    .health-subtitle { font-size: 13px; color: #5f6368; margin-bottom: 16px; }
    .health-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    .health-metric-label { font-size: 12px; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
    .health-metric-value { font-size: 28px; font-weight: 400; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .trend-arrow { font-size: 22px; }
    .trend-IMPROVING .trend-arrow { color: #1e8e3e; }
    .trend-STABLE .trend-arrow { color: #5f6368; }
    .trend-DEGRADING .trend-arrow { color: #d93025; }
    .sparkline-wrap { height: 48px; }
    .sparkline { width: 100%; height: 100%; display: block; }
    .degrading-banner { margin-top: 16px; padding: 12px 16px; background: #fce8e6; border-radius: 4px; font-size: 13px; color: #d93025; }
    .degrading-banner a { color: #d93025; font-weight: 500; }

    /* Filter bar */
    .filter-bar { display: flex; align-items: center; gap: 16px; padding: 12px 16px; border-bottom: 1px solid #e0e0e0; }
    .filter-bar label { font-size: 12px; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; }
    .filter-bar select { border: 1px solid #dadce0; border-radius: 4px; padding: 6px 10px; font-size: 13px; color: #202124; background: #fff; cursor: pointer; outline: none; }
    .filter-bar select:focus { border-color: #1a73e8; }

    /* Issue table */
    .table-card { overflow: hidden; }
    .issue-table { width: 100%; border-collapse: collapse; }
    .issue-table th { text-align: left; padding: 10px 16px; font-size: 11px; font-weight: 500; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; background: #fafafa; }
    .issue-row { border-bottom: 1px solid #f1f3f4; cursor: pointer; transition: background 0.1s; }
    .issue-row:hover { background: #f8f9fa; }
    .issue-row td { padding: 12px 16px; vertical-align: middle; }
    .issue-title { font-family: 'Roboto Mono', monospace; font-size: 12px; color: #202124; max-width: 420px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .issue-count { font-size: 14px; color: #202124; }
    .expand-icon { color: #5f6368; font-size: 12px; user-select: none; width: 24px; text-align: center; }

    /* Badges */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; white-space: nowrap; }
    .badge-P0 { background: #fce8e6; color: #d93025; }
    .badge-P1 { background: #fef7e0; color: #f29900; }
    .badge-P2 { background: #f1f3f4; color: #5f6368; }
    .badge-FRESH { background: #e6f4ea; color: #1e8e3e; }
    .badge-SPIKE { background: #f3e8fd; color: #a142f4; }
    .badge-CRASH { background: #e8f0fe; color: #1a73e8; }
    .badge-ANR { background: #fef0c7; color: #e37400; }
    .badges-cell { display: flex; gap: 4px; flex-wrap: wrap; min-width: 160px; }

    /* Detail row */
    .detail-row { display: none; background: #fafafa; border-bottom: 1px solid #e0e0e0; }
    .detail-row.open { display: table-row; }
    .detail-row td { padding: 16px 24px; }
    .detail-inner { display: flex; flex-direction: column; gap: 16px; }
    .detail-section h4 { font-size: 11px; font-weight: 500; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .stack-trace { font-family: 'Roboto Mono', monospace; font-size: 12px; background: #202124; color: #e8eaed; padding: 16px; border-radius: 4px; overflow-x: auto; max-height: 220px; white-space: pre; line-height: 1.6; }
    .fix-card { background: #fff; border-left: 3px solid #1a73e8; padding: 12px 16px; border-radius: 0 4px 4px 0; font-style: italic; color: #3c4043; line-height: 1.6; }
    .pr-list { display: flex; flex-wrap: wrap; gap: 8px; }
    .pr-chip { display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 6px 14px; border-radius: 16px; font-size: 12px; text-decoration: none; transition: background 0.1s; }
    .pr-chip:hover { background: #d2e3fc; }

    /* Empty state */
    .empty { text-align: center; padding: 48px; color: #5f6368; }

    @media (max-width: 768px) {
      .stats-row { grid-template-columns: 1fr 1fr; }
      .health-metrics { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>

<div class="header">
  <svg class="header-logo" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3L3 8.5V15.5L12 21L21 15.5V8.5L12 3Z" fill="#1a73e8" fill-opacity="0.15" stroke="#1a73e8" stroke-width="1.5"/>
    <path d="M12 7L6 10.5V17.5L12 21" stroke="#1a73e8" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M12 7L18 10.5V17.5L12 21" stroke="#34a853" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
  <h1>Crash &amp; ANR Report</h1>
  <span class="version-chip">v{{ previous_version }} → v{{ current_version }}</span>
  <span class="report-date">{{ report_date }}</span>
</div>

<div class="container">

  <div class="stats-row">
    <div class="card stat-card">
      <div class="stat-label">Total Issues</div>
      <div class="stat-value">{{ total }}</div>
    </div>
    <div class="card stat-card">
      <div class="stat-label">🆕 Fresh Issues</div>
      <div class="stat-value" style="color:#1e8e3e">{{ fresh_count }}</div>
    </div>
    <div class="card stat-card">
      <div class="stat-label">P0 Issues</div>
      <div class="stat-value" style="color:#d93025">{{ p0_count }}</div>
    </div>
    <div class="card stat-card">
      <div class="stat-label">⚡ Spiking</div>
      <div class="stat-value" style="color:#a142f4">{{ spike_count }}</div>
    </div>
  </div>

  <div class="card health-card">
    <h2>Session Health</h2>
    <p class="health-subtitle">30-day trend</p>
    <div class="health-metrics">
      <div class="trend-{{ session_health.trend }}">
        <div class="health-metric-label">Crash-Free Sessions</div>
        <div class="health-metric-value">
          {{ "%.1f"|format(session_health.crash_free_rate_today * 100) }}%
          <span class="trend-arrow">
            {%- if session_health.trend == "IMPROVING" %}↑
            {%- elif session_health.trend == "DEGRADING" %}↓
            {%- else %}→{%- endif %}
          </span>
        </div>
        <div class="sparkline-wrap">
          <canvas class="sparkline" id="crashSparkline"
            data-values="{{ session_health.daily_crash_free | join(',') }}"
            data-color="#1a73e8"></canvas>
        </div>
      </div>
      <div class="trend-{{ session_health.trend }}">
        <div class="health-metric-label">ANR-Free Sessions</div>
        <div class="health-metric-value">
          {{ "%.1f"|format(session_health.anr_free_rate_today * 100) }}%
          <span class="trend-arrow">
            {%- if session_health.trend == "IMPROVING" %}↑
            {%- elif session_health.trend == "DEGRADING" %}↓
            {%- else %}→{%- endif %}
          </span>
        </div>
        <div class="sparkline-wrap">
          <canvas class="sparkline" id="anrSparkline"
            data-values="{{ session_health.daily_anr_free | join(',') }}"
            data-color="#34a853"></canvas>
        </div>
      </div>
    </div>
    {% if session_health.trend == "DEGRADING" and session_health.driving_issue_ids %}
    <div class="degrading-banner">
      ⚠ Session health is declining. Top contributing issues:
      {% for issue_id in session_health.driving_issue_ids %}
        <a href="#row-{{ issue_id }}">{{ issue_id }}</a>{% if not loop.last %}, {% endif %}
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <div class="card table-card">
    <div class="filter-bar">
      <label>Type</label>
      <select id="filterType" onchange="applyFilters()">
        <option value="">All</option>
        <option value="CRASH">CRASH</option>
        <option value="ANR">ANR</option>
      </select>
      <label>Priority</label>
      <select id="filterPriority" onchange="applyFilters()">
        <option value="">All</option>
        <option value="P0">P0</option>
        <option value="P1">P1</option>
        <option value="P2">P2</option>
      </select>
      <label>Status</label>
      <select id="filterStatus" onchange="applyFilters()">
        <option value="">All</option>
        <option value="fresh">Fresh only</option>
        <option value="spike">Spiking only</option>
      </select>
    </div>
    <table class="issue-table">
      <thead>
        <tr>
          <th>Badges</th>
          <th>Issue</th>
          <th>Users</th>
          <th>First Seen</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for issue in issues %}
        <tr class="issue-row"
            id="row-{{ issue.id }}"
            data-type="{{ issue.issue_type }}"
            data-priority="{{ issue.priority_tier }}"
            data-fresh="{{ '1' if issue.is_fresh else '0' }}"
            data-spike="{{ '1' if issue.is_spike else '0' }}"
            onclick="toggle('{{ issue.id }}', this)">
          <td>
            <div class="badges-cell">
              <span class="badge badge-{{ issue.priority_tier }}">{{ issue.priority_tier }}</span>
              <span class="badge badge-{{ issue.issue_type }}">{{ issue.issue_type }}</span>
              {% if issue.is_fresh %}<span class="badge badge-FRESH">🆕 NEW</span>{% endif %}
              {% if issue.is_spike %}<span class="badge badge-SPIKE">⚡ SPIKE</span>{% endif %}
            </div>
          </td>
          <td><div class="issue-title">{{ issue.title }}</div></td>
          <td><span class="issue-count">{{ issue.user_count }}</span></td>
          <td>{{ issue.first_seen_version }}</td>
          <td><span class="expand-icon" id="icon-{{ issue.id }}">▶</span></td>
        </tr>
        <tr class="detail-row" id="detail-{{ issue.id }}">
          <td colspan="5">
            <div class="detail-inner">
              {% if issue.stack_trace %}
              <div class="detail-section">
                <h4>Stack Trace</h4>
                <div class="stack-trace">{{ issue.stack_trace }}</div>
              </div>
              {% endif %}
              {% if issue.fix_suggestion %}
              <div class="detail-section">
                <h4>Probable Fix (Gemini 1.5 Flash)</h4>
                <div class="fix-card">{{ issue.fix_suggestion }}</div>
              </div>
              {% endif %}
              {% if issue.is_fresh and issue.linked_prs %}
              <div class="detail-section">
                <h4>Recently Merged PRs Touching These Files</h4>
                <div class="pr-list">
                  {% for pr in issue.linked_prs %}
                  <a class="pr-chip" href="{{ pr.url }}" target="_blank" rel="noopener">
                    {{ pr.title }} · {{ pr.author }} · {{ pr.merge_date }}
                  </a>
                  {% endfor %}
                </div>
              </div>
              {% elif issue.is_fresh %}
              <div class="detail-section">
                <h4>PRs</h4>
                <p style="color:#5f6368;font-size:13px;">No recent PRs found touching these files.</p>
              </div>
              {% endif %}
            </div>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="empty">No issues found for v{{ current_version }}.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

</div>

<script>
function toggle(id, row) {
  const detail = document.getElementById('detail-' + id);
  const icon = document.getElementById('icon-' + id);
  const isOpen = detail.classList.contains('open');
  document.querySelectorAll('.detail-row.open').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.expand-icon').forEach(i => i.textContent = '▶');
  if (!isOpen) {
    detail.classList.add('open');
    icon.textContent = '▼';
  }
}

function applyFilters() {
  const type = document.getElementById('filterType').value;
  const priority = document.getElementById('filterPriority').value;
  const status = document.getElementById('filterStatus').value;
  document.querySelectorAll('.issue-row').forEach(row => {
    const okType = !type || row.dataset.type === type;
    const okPriority = !priority || row.dataset.priority === priority;
    const okStatus = !status
      || (status === 'fresh' && row.dataset.fresh === '1')
      || (status === 'spike' && row.dataset.spike === '1');
    row.style.display = (okType && okPriority && okStatus) ? '' : 'none';
    const detail = document.getElementById('detail-' + row.id.replace('row-', ''));
    if (detail && row.style.display === 'none') detail.classList.remove('open');
  });
}

function drawSparkline(canvas, values, color) {
  if (!values.length) return;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.offsetWidth;
  const h = canvas.offsetHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 0.001;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  values.forEach((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

document.querySelectorAll('.sparkline').forEach(canvas => {
  const vals = canvas.dataset.values.split(',').map(Number).filter(n => !isNaN(n));
  drawSparkline(canvas, vals, canvas.dataset.color || '#1a73e8');
});
</script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/report.html.jinja
git commit -m "feat: add Firebase Console-styled HTML report template"
```

---

## Task 11: ReportGenerator

**Files:**
- Create: `agent/report_generator.py`
- Create: `tests/test_report_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_report_generator.py`:

```python
import os
import tempfile
from agent.report_generator import generate_report
from agent.models import Issue, SessionHealth


def _issue(id: str, tier: str, is_fresh: bool, is_spike: bool) -> Issue:
    i = Issue(
        id=id, issue_type="CRASH",
        title="IllegalStateException in PlayerManager.kt:42",
        event_count=10, user_count=5, first_seen_version="1.1",
        last_seen_time="", stack_trace="at com.example.PlayerManager.start(PlayerManager.kt:42)",
    )
    i.priority_tier = tier
    i.is_fresh = is_fresh
    i.is_spike = is_spike
    i.fix_suggestion = "Check PlayerManager initialization."
    return i


def _health() -> SessionHealth:
    return SessionHealth(
        crash_free_rate_today=0.95,
        anr_free_rate_today=0.98,
        trend="STABLE",
        daily_crash_free=[0.95] * 10,
        daily_anr_free=[0.98] * 10,
    )


def test_generate_report_creates_html_file():
    issues = [_issue("A", "P0", True, False)]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_report(issues, _health(), "1.1", "1.0", output_dir=tmpdir)
    assert path.endswith("crash_report.html")


def test_generate_report_html_contains_issue_title():
    issues = [_issue("A", "P0", True, False)]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_report(issues, _health(), "1.1", "1.0", output_dir=tmpdir)
        content = open(path).read()
    assert "PlayerManager.kt:42" in content


def test_generate_report_html_contains_version_range():
    issues = []
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_report(issues, _health(), "1.1", "1.0", output_dir=tmpdir)
        content = open(path).read()
    assert "v1.0" in content
    assert "v1.1" in content


def test_generate_report_shows_fresh_badge_for_fresh_issue():
    issues = [_issue("A", "P0", is_fresh=True, is_spike=False)]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_report(issues, _health(), "1.1", "1.0", output_dir=tmpdir)
        content = open(path).read()
    assert "NEW" in content


def test_generate_report_shows_spike_badge_for_spiking_issue():
    issues = [_issue("A", "P1", is_fresh=False, is_spike=True)]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_report(issues, _health(), "1.1", "1.0", output_dir=tmpdir)
        content = open(path).read()
    assert "SPIKE" in content
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_report_generator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/report_generator.py`**

```python
import datetime
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import Issue, SessionHealth


def generate_report(
    issues: list[Issue],
    session_health: SessionHealth,
    current_version: str,
    previous_version: str,
    output_dir: str = "output",
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Resolve templates dir relative to this file's location
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report.html.jinja")

    html = template.render(
        issues=issues,
        session_health=session_health,
        current_version=current_version,
        previous_version=previous_version,
        total=len(issues),
        fresh_count=sum(1 for i in issues if i.is_fresh),
        spike_count=sum(1 for i in issues if i.is_spike),
        p0_count=sum(1 for i in issues if i.priority_tier == "P0"),
        p1_count=sum(1 for i in issues if i.priority_tier == "P1"),
        report_date=datetime.date.today().isoformat(),
    )

    output_path = os.path.join(output_dir, "crash_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_report_generator.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Run full test suite — verify nothing is broken**

```bash
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add agent/report_generator.py tests/test_report_generator.py
git commit -m "feat: add ReportGenerator — Jinja2 HTML report renderer"
```

---

## Task 12: Orchestrator

**Files:**
- Create: `agent/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_main.py`:

```python
import json
from unittest.mock import patch, MagicMock
from agent.main import run


SA_JSON = json.dumps({"type": "service_account", "project_id": "p"})

ENV = {
    "FIREBASE_SERVICE_ACCOUNT": SA_JSON,
    "FIREBASE_PROJECT_ID": "my-project",
    "FIREBASE_APP_ID": "1:123:android:abc",
    "GA4_PROPERTY_ID": "987654",
    "GITHUB_TOKEN": "ghp_fake",
    "GITHUB_REPO": "owner/demo-app",
    "GEMINI_API_KEY": "AIza-fake",
    "CURRENT_VERSION": "1.1",
    "PREVIOUS_VERSION": "1.0",
}


def test_run_calls_all_pipeline_steps(tmp_path):
    with patch.dict("os.environ", ENV), \
         patch("agent.main.get_access_token", return_value="tok"), \
         patch("agent.main.fetch_issues", return_value=[]) as mock_fetch, \
         patch("agent.main.detect_fresh", return_value=[]) as mock_fresh, \
         patch("agent.main.detect_spikes", return_value=[]) as mock_spike, \
         patch("agent.main.analyze_session_health", return_value=MagicMock()) as mock_health, \
         patch("agent.main.prioritize", return_value=[]) as mock_prio, \
         patch("agent.main.correlate", return_value=[]) as mock_corr, \
         patch("agent.main.suggest_fixes", return_value=[]) as mock_fix, \
         patch("agent.main.generate_report", return_value=str(tmp_path / "report.html")):
        run()

    assert mock_fetch.call_count == 2  # current + previous version
    mock_fresh.assert_called_once()
    mock_spike.assert_called_once()
    mock_health.assert_called_once()
    mock_prio.assert_called_once()
    mock_corr.assert_called_once()
    mock_fix.assert_called_once()
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_main.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `agent/main.py`**

```python
import json
import os

from .auth import get_access_token
from .crash_fetcher import fetch_issues
from .fix_suggester import suggest_fixes
from .fresh_detector import detect_fresh
from .git_correlator import correlate
from .prioritizer import prioritize
from .report_generator import generate_report
from .session_health_analyzer import analyze_session_health
from .spike_detector import detect_spikes


def run() -> None:
    sa_json = os.environ["FIREBASE_SERVICE_ACCOUNT"]
    project_id = os.environ["FIREBASE_PROJECT_ID"]
    app_id = os.environ["FIREBASE_APP_ID"]
    ga4_property_id = os.environ["GA4_PROPERTY_ID"]
    github_token = os.environ["GITHUB_TOKEN"]
    github_repo = os.environ["GITHUB_REPO"]
    gemini_key = os.environ["GEMINI_API_KEY"]
    current_version = os.environ.get("CURRENT_VERSION", "1.1")
    previous_version = os.environ.get("PREVIOUS_VERSION", "1.0")

    print(f"Fetching issues for v{current_version} and v{previous_version}...")
    token = get_access_token(sa_json)
    current = fetch_issues(token, project_id, app_id, current_version)
    previous = fetch_issues(token, project_id, app_id, previous_version)

    print(f"Found {len(current)} issues in v{current_version}, {len(previous)} in v{previous_version}")
    issues = detect_fresh(current, previous)
    issues = detect_spikes(issues, token, project_id, app_id, current_version)

    sa_info = json.loads(sa_json)
    health = analyze_session_health(sa_info, ga4_property_id, issues)
    print(f"Session health trend: {health.trend}")

    issues = prioritize(issues)
    issues = correlate(issues, github_token, github_repo)
    issues = suggest_fixes(issues, gemini_key)

    path = generate_report(issues, health, current_version, previous_version)
    print(f"Report written to {path}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_main.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add agent/main.py tests/test_main.py
git commit -m "feat: add orchestrator — run full pipeline in order"
```

---

## Task 13: Android demo app — Firebase Crashlytics SDK

**Files:**
- Modify: `build.gradle.kts`
- Modify: `app/build.gradle.kts`
- Modify: `app/src/main/AndroidManifest.xml`

**Prerequisite:** `app/google-services.json` must be present (downloaded from Firebase Console). It is gitignored — add it manually.

- [ ] **Step 1: Verify `google-services.json` is present**

```bash
ls app/google-services.json
```

Expected: file exists. If not, download from Firebase Console → Project Settings → Your app → download google-services.json → place in `app/`.

- [ ] **Step 2: Update `build.gradle.kts` (project level)**

Replace the entire file:

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    id("com.google.gms.google-services") version "4.4.2" apply false
    id("com.google.firebase.crashlytics") version "3.0.2" apply false
}
```

- [ ] **Step 3: Update `app/build.gradle.kts`**

Replace the plugins block (lines 1–4) with:

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}
```

Add to the `dependencies` block (before the closing `}`):

```kotlin
    implementation(platform("com.google.firebase:firebase-bom:33.1.0"))
    implementation("com.google.firebase:firebase-crashlytics-ktx")
    implementation("com.google.firebase:firebase-analytics-ktx")
```

- [ ] **Step 4: Add INTERNET permission to `app/src/main/AndroidManifest.xml`**

Add inside `<manifest>`, before `<application>`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

Add `android:usesCleartextTraffic="true"` to the `<application>` tag (needed for the NetworkOnMain demo crash):

```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

- [ ] **Step 5: Sync and build**

Open Android Studio → click "Sync Now" when prompted, or run:

```bash
./gradlew assembleDebug
```

Expected: `BUILD SUCCESSFUL`

- [ ] **Step 6: Commit**

```bash
git add build.gradle.kts app/build.gradle.kts app/src/main/AndroidManifest.xml
git commit -m "feat: add Firebase Crashlytics SDK to Android demo app"
```

---

## Task 14: Android demo app — Crash/ANR trigger UI

**Files:**
- Replace: `app/src/main/java/com/example/crashdemo/MainActivity.kt`

- [ ] **Step 1: Replace `MainActivity.kt`**

```kotlin
package com.example.crashdemo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.crashdemo.ui.theme.CrashDemoTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CrashDemoTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    CrashTriggerScreen()
                }
            }
        }
    }
}

@Composable
fun CrashTriggerScreen() {
    Column(
        modifier = Modifier
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("CrashDemo", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(4.dp))

        Text("v1.0 Issues (existing)", style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.outline)

        Button(onClick = { triggerNPE() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger NPE (CRASH)")
        }
        Button(onClick = { triggerIndexError() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger IndexOutOfBounds (CRASH)")
        }
        Button(onClick = { triggerANR() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger ANR — UI thread sleep")
        }

        Spacer(modifier = Modifier.height(8.dp))
        HorizontalDivider()
        Spacer(modifier = Modifier.height(8.dp))

        Text("v1.1 Issues (fresh)", style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.outline)

        Button(onClick = { triggerIllegalState() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger IllegalState (CRASH)")
        }
        Button(onClick = { triggerNetworkOnMain() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger NetworkOnMain (CRASH)")
        }
        Button(onClick = { triggerDeadlockANR() }, modifier = Modifier.fillMaxWidth()) {
            Text("Trigger Deadlock ANR")
        }
    }
}

// v1.0 crashes
fun triggerNPE() {
    val s: String? = null
    s!!.length
}

fun triggerIndexError() {
    listOf<Int>()[99]
}

fun triggerANR() {
    Thread.sleep(8000)  // blocks UI thread → ANR after 5s
}

// v1.1 crashes
fun triggerIllegalState() {
    check(false) { "PlayerManager failed to initialize" }
}

fun triggerNetworkOnMain() {
    java.net.URL("http://example.com").readText()  // NetworkOnMainThreadException
}

fun triggerDeadlockANR() {
    val lockA = Any()
    val lockB = Any()
    val thread = Thread {
        synchronized(lockB) {
            Thread.sleep(50)
            synchronized(lockA) { /* deadlock */ }
        }
    }
    thread.start()
    synchronized(lockA) {
        Thread.sleep(50)
        synchronized(lockB) { /* deadlock */ }
    }
}
```

- [ ] **Step 2: Build and verify**

```bash
./gradlew assembleDebug
```

Expected: `BUILD SUCCESSFUL`

- [ ] **Step 3: Populate v1.0 crash data**

```
1. Set versionCode = 1, versionName = "1.0" in app/build.gradle.kts (already set)
2. Install on emulator: ./gradlew installDebug
3. Open the app → tap "Trigger NPE" → app crashes → relaunch
4. Tap "Trigger IndexOutOfBounds" → crashes → relaunch
5. Tap "Trigger ANR — UI thread sleep" → wait for ANR dialog → press OK → relaunch
6. Repeat each button 2-3 times to generate enough events
7. Wait 5 minutes for Crashlytics to upload
8. Verify events appear in Firebase Console → Crashlytics
```

- [ ] **Step 4: Bump version and populate v1.1 crash data**

In `app/build.gradle.kts`, change:
```kotlin
versionCode = 2
versionName = "1.1"
```

Then:
```
1. ./gradlew installDebug
2. Tap all 6 buttons (both v1.0 and v1.1 sections) 2-3 times each
3. Wait 5 minutes for Crashlytics upload
4. Verify v1.1 issues appear in Firebase Console
5. Confirm v1.1-only issues are separate from v1.0 issues
```

- [ ] **Step 5: Commit**

```bash
git add app/src/main/java/com/example/crashdemo/MainActivity.kt app/build.gradle.kts
git commit -m "feat: add crash/ANR trigger buttons to demo app, bump to v1.1"
```

---

## Task 15: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/crash-report.yml`

- [ ] **Step 1: Verify GitHub repo secrets and variables are set**

Go to: `https://github.com/prashantprem/Crash-ANR-Prioritization-Agent/settings/secrets/actions`

Confirm these secrets exist:
- `FIREBASE_SERVICE_ACCOUNT` — full JSON content of the service account key
- `GEMINI_API_KEY`

And these variables (Settings → Variables → Actions):
- `FIREBASE_PROJECT_ID`
- `FIREBASE_APP_ID`
- `GA4_PROPERTY_ID`
- `GITHUB_REPO` — set to `prashantprem/Crash-ANR-Prioritization-Agent` (or the demo app repo if separate)

- [ ] **Step 2: Create `.github/workflows/crash-report.yml`**

```yaml
name: Crash & ANR Report

on:
  schedule:
    - cron: '0 9 * * *'   # Daily at 9 AM UTC
  workflow_dispatch:        # Manual trigger

jobs:
  generate-report:
    runs-on: ubuntu-latest
    permissions:
      contents: write       # needed for peaceiris/actions-gh-pages

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run agent
        run: python -m agent.main
        env:
          FIREBASE_SERVICE_ACCOUNT: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          FIREBASE_PROJECT_ID: ${{ vars.FIREBASE_PROJECT_ID }}
          FIREBASE_APP_ID: ${{ vars.FIREBASE_APP_ID }}
          GA4_PROPERTY_ID: ${{ vars.GA4_PROPERTY_ID }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPO: ${{ vars.GITHUB_REPO }}
          CURRENT_VERSION: "1.1"
          PREVIOUS_VERSION: "1.0"

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
          force_orphan: true
```

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/crash-report.yml
git commit -m "feat: add GitHub Actions workflow — daily crash report + Pages deploy"
git push origin main
```

- [ ] **Step 4: Enable GitHub Pages**

Go to: `https://github.com/prashantprem/Crash-ANR-Prioritization-Agent/settings/pages`

Set Source to: `Deploy from a branch` → branch: `gh-pages` → folder: `/ (root)` → Save.

- [ ] **Step 5: Trigger manual run**

Go to: `https://github.com/prashantprem/Crash-ANR-Prioritization-Agent/actions`

Click "Crash & ANR Report" → "Run workflow" → "Run workflow".

Watch the logs. Expected: all steps green, report deployed.

---

## Task 16: End-to-end smoke test

- [ ] **Step 1: Run full Python test suite one final time**

```bash
python -m pytest -v
```

Expected: all tests pass, no warnings about missing fixtures.

- [ ] **Step 2: Run agent locally with real credentials**

Create a `.env` file (gitignored):
```bash
export FIREBASE_SERVICE_ACCOUNT=$(cat path/to/service-account.json)
export FIREBASE_PROJECT_ID=your-project-id
export FIREBASE_APP_ID=1:xxx:android:xxx
export GA4_PROPERTY_ID=123456789
export GITHUB_TOKEN=ghp_your_token
export GITHUB_REPO=prashantprem/Crash-ANR-Prioritization-Agent
export GEMINI_API_KEY=AIza-your-key
export CURRENT_VERSION=1.1
export PREVIOUS_VERSION=1.0
```

Run:
```bash
source .env && python -m agent.main
```

Expected output:
```
Fetching issues for v1.1 and v1.0...
Found N issues in v1.1, M issues in v1.0
Session health trend: STABLE  (or IMPROVING/DEGRADING)
Report written to output/crash_report.html
```

- [ ] **Step 3: Open report in browser**

```bash
open output/crash_report.html
```

Verify:
- Header shows `v1.0 → v1.1` and today's date
- Summary cards show correct counts
- Session health sparklines render
- v1.1-only issues have `🆕 NEW` badge
- Click a row → stack trace, fix suggestion, PR list (if fresh) expand correctly
- Filters for Type / Priority / Status work

- [ ] **Step 4: If any field names are wrong from Crashlytics API**

Edit `agent/crash_fetcher.py` `_parse_issue()` to match actual API response keys. Use:
```bash
python -c "
import json, requests
from agent.auth import get_access_token
import os
tok = get_access_token(os.environ['FIREBASE_SERVICE_ACCOUNT'])
r = requests.get(
  'https://crashlytics.googleapis.com/v1alpha/projects/YOUR_PROJECT/apps/YOUR_APP/issues',
  headers={'Authorization': f'Bearer {tok}'},
  params={'pageSize': 1}
)
print(json.dumps(r.json(), indent=2))
"
```

This shows the raw API response — use the actual field names in `_parse_issue()`.

- [ ] **Step 5: Final commit and push**

```bash
git add -A
git commit -m "chore: verified end-to-end — report generates and deploys correctly"
git push origin main
```

Report will be live at: `https://prashantprem.github.io/Crash-ANR-Prioritization-Agent/crash_report.html`
