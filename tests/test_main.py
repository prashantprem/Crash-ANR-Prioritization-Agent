import json
from unittest.mock import patch, MagicMock
from agent.main import run


SA_JSON = json.dumps({"type": "service_account", "project_id": "p"})

ENV = {
    "FIREBASE_SERVICE_ACCOUNT": SA_JSON,
    "FIREBASE_PROJECT_ID": "my-project",
    "FIREBASE_APP_PACKAGE": "com.example.crashdemo",
    "GA4_PROPERTY_ID": "987654",
    "GITHUB_TOKEN": "ghp_fake",
    "TARGET_REPO": "owner/demo-app",
    "GEMINI_API_KEY": "AIza-fake",
    "CURRENT_VERSION": "1.1",
    "PREVIOUS_VERSION": "1.0",
}


def test_run_calls_all_pipeline_steps(tmp_path):
    with patch.dict("os.environ", ENV), \
         patch("agent.main.get_bigquery_client", return_value=MagicMock()) as mock_bq, \
         patch("agent.main.fetch_issues", return_value=[]) as mock_fetch, \
         patch("agent.main.detect_fresh", return_value=[]) as mock_fresh, \
         patch("agent.main.detect_spikes", return_value=[]) as mock_spike, \
         patch("agent.main.analyze_session_health", return_value=MagicMock()) as mock_health, \
         patch("agent.main.prioritize", return_value=[]) as mock_prio, \
         patch("agent.main.correlate", return_value=[]) as mock_corr, \
         patch("agent.main.suggest_fixes", return_value=[]) as mock_fix, \
         patch("agent.main.generate_report", return_value=str(tmp_path / "report.html")):
        run()

    mock_bq.assert_called_once()
    assert mock_fetch.call_count == 2  # current + previous version
    mock_fresh.assert_called_once()
    mock_spike.assert_called_once()
    mock_health.assert_called_once()
    mock_prio.assert_called_once()
    mock_corr.assert_called_once()
    mock_fix.assert_called_once()
