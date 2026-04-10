from agent.fresh_detector import detect_fresh
from agent.models import Issue


def _issue(id: str) -> Issue:
    return Issue(
        id=id, issue_type="CRASH", title="Test", event_count=10,
        user_count=5, first_seen_version="1.1",
        last_seen_time="2026-04-10T09:00:00Z", stack_trace="",
    )


def test_marks_issues_absent_in_previous_as_fresh():
    current = [_issue("A"), _issue("B"), _issue("C")]
    previous = [_issue("A")]
    result = detect_fresh(current, previous)
    assert result[0].is_fresh is False
    assert result[1].is_fresh is True
    assert result[2].is_fresh is True


def test_no_fresh_when_all_issues_match():
    current = [_issue("A"), _issue("B")]
    previous = [_issue("A"), _issue("B")]
    result = detect_fresh(current, previous)
    assert all(not i.is_fresh for i in result)


def test_all_fresh_when_previous_is_empty():
    current = [_issue("X"), _issue("Y")]
    result = detect_fresh(current, [])
    assert all(i.is_fresh for i in result)


def test_returns_same_list_mutated_in_place():
    current = [_issue("A")]
    result = detect_fresh(current, [])
    assert result is current
