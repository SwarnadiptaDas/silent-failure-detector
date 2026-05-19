from datetime import datetime, timedelta
from typing import List, Dict
import re


def parse_repo_url(url_or_slug: str) -> tuple[str, str] | None:
    """
    Parse a GitHub repo URL or 'owner/repo' slug.
    Returns (owner, repo) or None if invalid.
    """
    url_or_slug = url_or_slug.strip().rstrip("/")

    # Full URL: https://github.com/owner/repo
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url_or_slug)
    if match:
        return match.group(1), match.group(2)

    # Slug: owner/repo
    parts = url_or_slug.split("/")
    if len(parts) == 2 and all(p.strip() for p in parts):
        return parts[0].strip(), parts[1].strip()

    return None


def format_risk_badge(label: str) -> str:
    """Return an emoji badge for a risk label."""
    badges = {
        "Critical": "🔴",
        "High":     "🟠",
        "Medium":   "🟡",
        "Low":      "🟢",
        "Healthy":  "✅",
    }
    return badges.get(label, "⚪")


def days_since(date_str: str) -> int:
    """Return number of days since a date string (YYYY-MM-DD)."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (datetime.utcnow().date() - d).days
    except (ValueError, TypeError):
        return 0


def stale_pr_count(prs: List[dict], threshold_days: int = 14) -> int:
    """Count PRs open for longer than threshold_days."""
    return sum(
        1 for pr in prs
        if pr.get("state") == "open" and days_since(pr.get("updated_at", "")) >= threshold_days
    )


def bus_factor(contributors: List[dict]) -> int:
    """
    Estimate bus factor: minimum contributors whose removal
    would drop total contributions below 50%.
    """
    if not contributors:
        return 0
    total = sum(c.get("contributions", 0) for c in contributors)
    if total == 0:
        return 0
    cumulative = 0
    for i, c in enumerate(sorted(contributors, key=lambda x: -x.get("contributions", 0))):
        cumulative += c.get("contributions", 0)
        if cumulative / total >= 0.5:
            return i + 1
    return len(contributors)


def commit_frequency_last_n_days(commits: List[dict], n: int = 30) -> float:
    """Return average commits per week over the last n days."""
    cutoff = datetime.utcnow().date() - timedelta(days=n)
    recent = [c for c in commits
              if datetime.strptime(c["date"][:10], "%Y-%m-%d").date() >= cutoff]
    total_commits = sum(c.get("count", 1) for c in recent)
    weeks = n / 7
    return round(total_commits / weeks, 2)


def severity_color(score: float) -> str:
    """Map a 0–100 score to a traffic-light hex color."""
    if score >= 75:
        return "#E53935"
    elif score >= 55:
        return "#FB8C00"
    elif score >= 35:
        return "#FDD835"
    return "#43A047"
