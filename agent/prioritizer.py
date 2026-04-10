from .models import Issue


def prioritize(issues: list[Issue]) -> list[Issue]:
    for issue in issues:
        base = issue.user_count * max(issue.event_count, 1)
        fresh_mult = 1.5 if issue.is_fresh else 1.0
        spike_mult = 1.3 if issue.is_spike else 1.0
        issue.priority_score = base * fresh_mult * spike_mult

    issues.sort(key=lambda i: i.priority_score, reverse=True)
    n = len(issues)
    p0_cutoff = max(1, round(n * 0.10))
    p1_cutoff = max(1, round(n * 0.40))

    for idx, issue in enumerate(issues):
        if idx < p0_cutoff:
            issue.priority_tier = "P0"
        elif idx < p1_cutoff:
            issue.priority_tier = "P1"
        else:
            issue.priority_tier = "P2"

    return issues
