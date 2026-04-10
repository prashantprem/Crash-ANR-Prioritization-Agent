from urllib.parse import quote

import requests

from .models import Issue

CRASHLYTICS_BASE = "https://crashlytics.googleapis.com/v1alpha"


def fetch_issues(
    token: str, project_id: str, app_id: str, version: str
) -> list[Issue]:
    app_id_encoded = quote(app_id, safe="")
    url = f"{CRASHLYTICS_BASE}/projects/{project_id}/apps/{app_id_encoded}/issues"
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
        if not resp.ok:
            print(f"[crash_fetcher] HTTP {resp.status_code} — {resp.text}")
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
