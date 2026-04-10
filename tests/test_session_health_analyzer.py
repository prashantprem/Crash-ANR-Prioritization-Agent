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
    rates = [0.97] * 7 + [0.90, 0.90, 0.90]
    assert _compute_trend(rates) == "DEGRADING"


def test_compute_trend_returns_improving_when_recent_better():
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
