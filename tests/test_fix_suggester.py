from unittest.mock import patch, MagicMock
from agent.fix_suggester import suggest_fixes
from agent.models import Issue


def _issue(id: str, stack_trace: str = "at com.example.Foo.bar(Foo.kt:1)") -> Issue:
    return Issue(
        id=id, issue_type="CRASH", title="Test", event_count=1,
        user_count=1, first_seen_version="1.1", last_seen_time="", stack_trace=stack_trace,
    )


def test_suggest_fixes_populates_fix_suggestion_for_all_issues():
    issues = [_issue("A"), _issue("B")]
    mock_response = MagicMock()
    mock_response.text = "Check for null before accessing the field."

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.return_value = mock_response
        result = suggest_fixes(issues, "fake-api-key")

    assert result[0].fix_suggestion == "Check for null before accessing the field."
    assert result[1].fix_suggestion == "Check for null before accessing the field."


def test_suggest_fixes_handles_api_error_gracefully():
    issues = [_issue("A")]

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.side_effect = Exception("API quota exceeded")
        result = suggest_fixes(issues, "fake-key")

    assert result[0].fix_suggestion == "Unable to generate suggestion."


def test_suggest_fixes_sends_stack_trace_in_prompt():
    issues = [_issue("A", stack_trace="at com.example.Foo.crash(Foo.kt:99)")]
    mock_response = MagicMock()
    mock_response.text = "Fix it."

    with patch("agent.fix_suggester.genai.GenerativeModel") as mock_model_cls:
        mock_model = mock_model_cls.return_value
        mock_model.generate_content.return_value = mock_response
        suggest_fixes(issues, "key")

    prompt = mock_model.generate_content.call_args[0][0]
    assert "Foo.kt:99" in prompt
