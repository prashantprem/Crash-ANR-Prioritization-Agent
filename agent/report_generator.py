import datetime
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import Issue, SessionHealth


def generate_report(
    issues: list[Issue],
    session_health: SessionHealth,
    current_version: str,
    previous_version: str,
    output_dir: str = "output",
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Resolve templates dir relative to this file's location
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report.html.jinja")

    html = template.render(
        issues=issues,
        session_health=session_health,
        current_version=current_version,
        previous_version=previous_version,
        total=len(issues),
        fresh_count=sum(1 for i in issues if i.is_fresh),
        spike_count=sum(1 for i in issues if i.is_spike),
        p0_count=sum(1 for i in issues if i.priority_tier == "P0"),
        p1_count=sum(1 for i in issues if i.priority_tier == "P1"),
        report_date=datetime.date.today().isoformat(),
    )

    output_path = os.path.join(output_dir, "crash_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
