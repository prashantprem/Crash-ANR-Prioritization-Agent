from .models import Issue


def detect_spikes(
    issues: list[Issue],
    bq_client,
    project_id: str,
    app_package: str,
    version: str,
) -> list[Issue]:
    non_fresh = [i for i in issues if not i.is_fresh]
    if not non_fresh:
        return issues

    table_name = app_package.replace(".", "_") + "_ANDROID"

    seven_day_counts = _query_event_counts(bq_client, project_id, table_name, version, hours_ago=168)
    today_counts = _query_event_counts(bq_client, project_id, table_name, version, hours_ago=24)

    for issue in issues:
        if issue.is_fresh:
            continue
        today = today_counts.get(issue.id, 0)
        weekly_avg = seven_day_counts.get(issue.id, 0) / 7
        if weekly_avg > 0 and today > 2 * weekly_avg:
            issue.is_spike = True

    return issues


def _query_event_counts(
    bq_client, project_id: str, table_name: str, version: str, hours_ago: int
) -> dict[str, int]:
    from google.cloud import bigquery

    full_table = f"`{project_id}.firebase_crashlytics.{table_name}`"
    query = f"""
        SELECT issue_id, COUNT(*) AS cnt
        FROM {full_table}
        WHERE application.display_version = @version
          AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
        GROUP BY issue_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("version", "STRING", version),
            bigquery.ScalarQueryParameter("hours", "INT64", hours_ago),
        ]
    )
    try:
        results = bq_client.query(query, job_config=job_config).result()
        return {row.issue_id: row.cnt for row in results}
    except Exception as e:
        print(f"[spike_detector] BigQuery error: {e}")
        return {}
