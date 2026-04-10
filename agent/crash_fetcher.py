from google.api_core.exceptions import NotFound

from .models import Issue


def fetch_issues(bq_client, project_id: str, app_package: str, version: str) -> list[Issue]:
    table_name = app_package.replace(".", "_") + "_ANDROID"
    full_table = f"`{project_id}.firebase_crashlytics.{table_name}`"

    query = f"""
        SELECT
          issue_id,
          ANY_VALUE(error_type) AS error_type,
          ANY_VALUE(COALESCE(exceptions[SAFE_OFFSET(0)].type, 'Unknown')) AS exception_type,
          ANY_VALUE(COALESCE(blame_frame.file, '')) AS blame_file,
          ANY_VALUE(blame_frame.line) AS blame_line,
          COUNT(*) AS event_count,
          COUNT(DISTINCT installation_uuid) AS user_count,
          MAX(event_timestamp) AS last_seen
        FROM {full_table}
        WHERE application.display_version = @version
        GROUP BY issue_id
        ORDER BY user_count DESC
        LIMIT 200
    """

    from google.cloud import bigquery

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("version", "STRING", version)
        ]
    )

    try:
        results = bq_client.query(query, job_config=job_config).result()
    except NotFound:
        print(f"[crash_fetcher] BigQuery table not found: {table_name}. "
              "Ensure Crashlytics BigQuery export is enabled and data has synced.")
        return []

    issues = []
    for row in results:
        error_type = (row.error_type or "FATAL").upper()
        issue_type = "ANR" if error_type == "ANR" else "CRASH"
        exception_type = row.exception_type or "Unknown"
        blame_file = row.blame_file or ""
        blame_line = str(row.blame_line) if row.blame_line is not None else ""

        title = (
            f"{exception_type} in {blame_file}:{blame_line}"
            if blame_file else exception_type
        )
        stack_trace = (
            f"at {exception_type}({blame_file}:{blame_line})"
            if blame_file else ""
        )

        issues.append(Issue(
            id=row.issue_id,
            issue_type=issue_type,
            title=title,
            event_count=row.event_count,
            user_count=row.user_count,
            first_seen_version=version,
            last_seen_time=str(row.last_seen) if row.last_seen else "",
            stack_trace=stack_trace,
        ))

    return issues
