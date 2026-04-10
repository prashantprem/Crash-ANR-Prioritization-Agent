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
