from .models import Issue


def detect_fresh(
    current_issues: list[Issue], previous_issues: list[Issue]
) -> list[Issue]:
    previous_ids = {issue.id for issue in previous_issues}
    for issue in current_issues:
        issue.is_fresh = issue.id not in previous_ids
    return current_issues
