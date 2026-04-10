from dataclasses import dataclass, field


@dataclass
class LinkedPR:
    title: str
    author: str
    merge_date: str
    url: str


@dataclass
class Issue:
    id: str
    issue_type: str          # "CRASH" or "ANR"
    title: str
    event_count: int
    user_count: int
    first_seen_version: str
    last_seen_time: str      # ISO 8601 string
    stack_trace: str
    is_fresh: bool = False
    is_spike: bool = False
    priority_score: float = 0.0
    priority_tier: str = ""  # "P0", "P1", or "P2"
    linked_prs: list = field(default_factory=list)
    fix_suggestion: str = ""


@dataclass
class SessionHealth:
    crash_free_rate_today: float
    anr_free_rate_today: float
    trend: str               # "IMPROVING", "STABLE", or "DEGRADING"
    driving_issue_ids: list = field(default_factory=list)
    daily_crash_free: list = field(default_factory=list)
    daily_anr_free: list = field(default_factory=list)
