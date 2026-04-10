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


def test_flags_issue_as_spike_when_today_exceeds_twice_weekly_avg():
    issues = [_issue("A")]
    mock_client = MagicMock()

    with patch("agent.spike_detector._query_event_counts") as mock_q:
        # 7-day total = 7, daily avg = 1; today = 3 → 3 > 2×1 → SPIKE
        mock_q.side_effect = [{"A": 7}, {"A": 3}]
        result = detect_spikes(issues, mock_client, "proj", "com.example.app", "1.1")

    assert result[0].is_spike is True


def test_does_not_flag_when_today_within_normal_range():
    issues = [_issue("A")]
    mock_client = MagicMock()

    with patch("agent.spike_detector._query_event_counts") as mock_q:
        # 7-day total = 70, daily avg = 10; today = 12 → 12 < 2×10 → no spike
        mock_q.side_effect = [{"A": 70}, {"A": 12}]
        result = detect_spikes(issues, mock_client, "proj", "com.example.app", "1.1")

    assert result[0].is_spike is False


def test_fresh_issues_skip_spike_detection():
    issues = [_issue("A", is_fresh=True)]
    mock_client = MagicMock()

    with patch("agent.spike_detector._query_event_counts") as mock_q:
        result = detect_spikes(issues, mock_client, "proj", "com.example.app", "1.1")

    mock_q.assert_not_called()
    assert result[0].is_spike is False


def test_no_spike_when_weekly_avg_is_zero():
    issues = [_issue("A")]
    mock_client = MagicMock()

    with patch("agent.spike_detector._query_event_counts") as mock_q:
        mock_q.side_effect = [{"A": 0}, {"A": 5}]
        result = detect_spikes(issues, mock_client, "proj", "com.example.app", "1.1")

    assert result[0].is_spike is False
