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
