import re
from typing import Optional

import requests

from .models import Issue, LinkedPR

GITHUB_API = "https://api.github.com"


def correlate(issues: list[Issue], token: str, repo: str) -> list[Issue]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for issue in issues:
        if not issue.is_fresh:
            continue
        files = _extract_files(issue.stack_trace)
        prs: list[LinkedPR] = []
        seen_urls: set[str] = set()
        for file_path in files[:3]:
            for sha in _get_recent_commits(headers, repo, file_path):
                pr = _get_pr_for_commit(headers, repo, sha)
                if pr and pr.url not in seen_urls:
                    seen_urls.add(pr.url)
                    prs.append(pr)
        issue.linked_prs = prs[:5]
    return issues


def _extract_files(stack_trace: str) -> list[str]:
    pattern = r"at ([\w.]+)\((\w+\.kt):\d+\)"
    seen: set[str] = set()
    files: list[str] = []
    for pkg_method, filename in re.findall(pattern, stack_trace):
        # pkg_method is like com.example.crashdemo.PlayerManager.start
        # The filename stem (e.g. "PlayerManager") identifies the class.
        # Strip method name AND class name to get the package, then re-append filename.
        class_stem = filename.rsplit(".", 1)[0]  # e.g. "PlayerManager"
        # Split on the class name to find the package prefix
        dot_class = f".{class_stem}."
        if dot_class in pkg_method:
            pkg = pkg_method.split(dot_class)[0]  # com.example.crashdemo
            path = f"{pkg.replace('.', '/')}/{filename}"
        else:
            # Fallback: drop last two components (method + class)
            parts = pkg_method.split(".")
            pkg = ".".join(parts[:-2]) if len(parts) > 2 else parts[0]
            path = f"{pkg.replace('.', '/')}/{filename}"
        if path not in seen:
            seen.add(path)
            files.append(path)
    return files


def _get_recent_commits(headers: dict, repo: str, file_path: str) -> list[str]:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/commits",
        headers=headers,
        params={"path": file_path, "per_page": 5},
    )
    if resp.status_code != 200:
        return []
    return [c["sha"] for c in resp.json()]


def _get_pr_for_commit(headers: dict, repo: str, sha: str) -> Optional[LinkedPR]:
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/commits/{sha}/pulls",
        headers=headers,
    )
    if resp.status_code != 200 or not resp.json():
        return None
    pr = resp.json()[0]
    merged_at = pr.get("merged_at") or ""
    url = pr["html_url"]
    if not url.startswith("https://"):
        return None
    return LinkedPR(
        title=pr["title"],
        author=pr["user"]["login"],
        merge_date=merged_at[:10],
        url=url,
    )
