from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

from .models import Issue, SessionHealth

CRASH_METRIC = "crashAffectedUsersRate"
ANR_METRIC = "anrAffectedUsersRate"


def analyze_session_health(
    service_account_info: dict,
    property_id: str,
    issues: list[Issue],
) -> SessionHealth:
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name=CRASH_METRIC), Metric(name=ANR_METRIC)],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
    )

    try:
        response = client.run_report(request)
    except Exception as e:
        print(f"[session_health] GA4 error: {e}")
        print("[session_health] Returning default STABLE health — grant the service account Viewer access in GA4 Property Access Management")
        return SessionHealth(
            crash_free_rate_today=1.0,
            anr_free_rate_today=1.0,
            trend="STABLE",
        )

    daily_crash_free = []
    daily_anr_free = []

    for row in response.rows:
        crash_rate = float(row.metric_values[0].value or 0)
        anr_rate = float(row.metric_values[1].value or 0)
        daily_crash_free.append(1.0 - crash_rate)
        daily_anr_free.append(1.0 - anr_rate)

    trend = _compute_trend(daily_crash_free)
    driving_ids = _find_drivers(issues, trend)

    return SessionHealth(
        crash_free_rate_today=daily_crash_free[-1] if daily_crash_free else 1.0,
        anr_free_rate_today=daily_anr_free[-1] if daily_anr_free else 1.0,
        trend=trend,
        driving_issue_ids=driving_ids,
        daily_crash_free=daily_crash_free,
        daily_anr_free=daily_anr_free,
    )


def _compute_trend(daily_rates: list[float]) -> str:
    if len(daily_rates) < 10:
        return "STABLE"
    recent = sum(daily_rates[-3:]) / 3
    older_slice = daily_rates[-10:-3]
    older = sum(older_slice) / len(older_slice)
    delta = recent - older
    if delta > 0.005:
        return "IMPROVING"
    if delta < -0.005:
        return "DEGRADING"
    return "STABLE"


def _find_drivers(issues: list[Issue], trend: str) -> list[str]:
    if trend != "DEGRADING":
        return []
    sorted_issues = sorted(issues, key=lambda i: i.user_count, reverse=True)
    return [i.id for i in sorted_issues[:3]]
