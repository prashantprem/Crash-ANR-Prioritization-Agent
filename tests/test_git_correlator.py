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
