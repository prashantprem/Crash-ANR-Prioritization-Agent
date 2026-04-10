from unittest.mock import MagicMock
from google.api_core.exceptions import NotFound
from agent.crash_fetcher import fetch_issues


def _make_row(issue_id, error_type, exception_type, blame_file, blame_line,
              event_count, user_count, last_seen="2026-04-10"):
    row = MagicMock()
    row.issue_id = issue_id
    row.error_type = error_type
    row.exception_type = exception_type
    row.blame_file = blame_file
    row.blame_line = blame_line
    row.event_count = event_count
    row.user_count = user_count
    row.last_seen = last_seen
    return row


def _make_bq_client(rows):
    client = MagicMock()
    job = MagicMock()
    job.result.return_value = rows
    client.query.return_value = job
    return client


def test_fetch_issues_returns_issue_list():
    rows = [
        _make_row("abc123", "FATAL", "NullPointerException", "HomeViewModel.kt", 55, 42, 10),
        _make_row("def456", "ANR", "ANR", "MainActivity.kt", 10, 5, 3),
    ]
    issues = fetch_issues(_make_bq_client(rows), "proj", "com.example.app", "1.1")
    assert len(issues) == 2


def test_fetch_issues_parses_fields_correctly():
    rows = [
        _make_row("abc123", "FATAL", "NullPointerException", "HomeViewModel.kt", 55, 42, 10),
        _make_row("def456", "ANR", "ANR", "MainActivity.kt", 10, 5, 3),
    ]
    issues = fetch_issues(_make_bq_client(rows), "proj", "com.example.app", "1.1")

    crash = issues[0]
    assert crash.id == "abc123"
    assert crash.issue_type == "CRASH"
    assert crash.event_count == 42
    assert crash.user_count == 10
    assert "HomeViewModel" in crash.stack_trace

    anr = issues[1]
    assert anr.issue_type == "ANR"


def test_fetch_issues_returns_empty_on_not_found():
    client = MagicMock()
    job = MagicMock()
    job.result.side_effect = NotFound("table not found")
    client.query.return_value = job
    issues = fetch_issues(client, "proj", "com.example.app", "1.1")
    assert issues == []
