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

    # Skip all API calls if there are no non-fresh issues to check
    non_fresh = [i for i in issues if not i.is_fresh]
    if not non_fresh:
        return issues

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
    url = f"{CRASHLYTICS_BASE}/projects/{project_id}/apps/{app_id}/issues"
    headers = {"Authorization": f"Bearer {token}"}
    counts: dict[str, int] = {}
    page_token = None

    while True:
        params: dict = {
            "filter": f'appVersion="{version}" AND lastSeenTime>"{since}"',
            "pageSize": 100,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("issues", []):
            issue_id = item["name"].split("/")[-1]
            counts[issue_id] = int(item.get("eventCount", 0))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return counts
