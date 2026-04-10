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
