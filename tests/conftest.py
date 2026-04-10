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
