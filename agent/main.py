import json
import os

from .auth import get_access_token
from .crash_fetcher import fetch_issues
from .fix_suggester import suggest_fixes
from .fresh_detector import detect_fresh
from .git_correlator import correlate
from .prioritizer import prioritize
from .report_generator import generate_report
from .session_health_analyzer import analyze_session_health
from .spike_detector import detect_spikes


def run() -> None:
    sa_json = os.environ["FIREBASE_SERVICE_ACCOUNT"]
    sa_info = json.loads(sa_json)  # validate JSON early — fail fast on bad credentials
    project_id = os.environ["FIREBASE_PROJECT_ID"]
    app_id = os.environ["FIREBASE_APP_ID"]
    ga4_property_id = os.environ["GA4_PROPERTY_ID"]
    github_token = os.environ["GITHUB_TOKEN"]
    github_repo = os.environ["TARGET_REPO"]
    gemini_key = os.environ["GEMINI_API_KEY"]
    current_version = os.environ.get("CURRENT_VERSION", "1.1")
    previous_version = os.environ.get("PREVIOUS_VERSION", "1.0")

    print(f"Fetching issues for v{current_version} and v{previous_version}...")
    token = get_access_token(sa_json)
    current = fetch_issues(token, project_id, app_id, current_version)
    previous = fetch_issues(token, project_id, app_id, previous_version)

    print(f"Found {len(current)} issues in v{current_version}, {len(previous)} in v{previous_version}")
    issues = detect_fresh(current, previous)
    issues = detect_spikes(issues, token, project_id, app_id, current_version)

    health = analyze_session_health(sa_info, ga4_property_id, issues)
    print(f"Session health trend: {health.trend}")

    issues = prioritize(issues)
    issues = correlate(issues, github_token, github_repo)
    issues = suggest_fixes(issues, gemini_key)

    path = generate_report(issues, health, current_version, previous_version)
    print(f"Report written to {path}")


if __name__ == "__main__":
    run()
