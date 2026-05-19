from datetime import datetime, timedelta
from typing import Dict, List
import math


def compute_risk_score(data: dict, sentiment_result: dict) -> dict:
    """
    Compute a holistic project failure risk score (0–100).

    Dimensions:
      1. Commit velocity decay    (25%)
      2. PR stagnation            (20%)
      3. Issue accumulation       (20%)
      4. Contributor disengagement(20%)
      5. Sentiment / comms health (15%)
    """
    commits    = data.get("commits", [])
    prs        = data.get("pull_requests", [])
    issues     = data.get("issues", [])
    contributors = data.get("contributors", [])

    scores = {}

    scores["commit_decay"]    = _score_commit_decay(commits)
    scores["pr_stagnation"]   = _score_pr_stagnation(prs)
    scores["issue_backlog"]   = _score_issue_backlog(issues)
    scores["contributor_disengagement"] = _score_contributor_disengagement(contributors, commits)
    scores["sentiment_risk"]  = round(sentiment_result.get("risk_contribution", 0.0) * 100, 1)

    weights = {
        "commit_decay":    0.25,
        "pr_stagnation":   0.20,
        "issue_backlog":   0.20,
        "contributor_disengagement": 0.20,
        "sentiment_risk":  0.15,
    }

    overall = sum(scores[k] * weights[k] for k in weights)
    overall = round(min(100.0, max(0.0, overall)), 1)

    return {
        "overall": overall,
        "label": _risk_label(overall),
        "color": _risk_color(overall),
        "dimensions": scores,
        "weights": weights,
        "bottlenecks": _identify_bottlenecks(scores),
        "trend": _estimate_trend(commits),
    }


# ── Individual scorers ──────────────────────────────────────────────────────

def _score_commit_decay(commits: List[dict]) -> float:
    """Compare recent 30-day commit count to prior 30-day count."""
    if not commits:
        return 80.0

    now = datetime.utcnow().date()
    recent_cutoff = now - timedelta(days=30)
    prior_cutoff  = now - timedelta(days=60)

    recent = sum(c["count"] for c in commits
                 if _parse_date(c["date"]) >= recent_cutoff)
    prior  = sum(c["count"] for c in commits
                 if prior_cutoff <= _parse_date(c["date"]) < recent_cutoff)

    if prior == 0:
        return 70.0 if recent == 0 else 10.0

    decay_ratio = 1.0 - (recent / prior)
    # decay_ratio: 1.0 = total stop, 0 = same pace, negative = acceleration
    score = max(0.0, min(100.0, decay_ratio * 100))
    return round(score, 1)


def _score_pr_stagnation(prs: List[dict]) -> float:
    """Penalise old open PRs with low / zero comments."""
    if not prs:
        return 20.0

    open_prs = [pr for pr in prs if pr.get("state") == "open"]
    if not open_prs:
        return 10.0

    now = datetime.utcnow().date()
    stale_scores = []
    for pr in open_prs:
        updated = _parse_date(pr.get("updated_at", str(now)))
        age_days = max(0, (now - updated).days)
        comments = pr.get("comments", 0)

        age_score     = min(100, age_days * 2)        # 50+ days → 100
        silence_score = max(0, 60 - comments * 15)    # 0 comments → 60, 4+ → 0

        stale_scores.append((age_score + silence_score) / 2)

    return round(sum(stale_scores) / len(stale_scores), 1)


def _score_issue_backlog(issues: List[dict]) -> float:
    """Score based on open-issue count and critical labels."""
    open_issues = [i for i in issues if i.get("state") == "open"]
    critical    = [i for i in open_issues
                   if any(l in ["critical", "bug", "regression", "blocker"]
                          for l in i.get("labels", []))]
    silent      = [i for i in open_issues if i.get("comments", 0) == 0]

    count_score    = min(100, len(open_issues) * 4)
    critical_score = min(100, len(critical) * 15)
    silent_score   = min(100, len(silent) * 8)

    return round((count_score * 0.4 + critical_score * 0.4 + silent_score * 0.2), 1)


def _score_contributor_disengagement(contributors: List[dict], commits: List[dict]) -> float:
    """Flag projects with single-author dependency or dropping contributor count."""
    if not contributors:
        return 60.0

    total_contributions = sum(c.get("contributions", 0) for c in contributors) or 1
    top_share = contributors[0].get("contributions", 0) / total_contributions

    # Bus-factor risk: one person does >70% of the work
    bus_factor_score = min(100, max(0, (top_share - 0.5) / 0.5 * 100))

    # Recency: how recently was each contributor last active?
    now = datetime.utcnow().date()
    recency_scores = []
    for c in contributors:
        last = _parse_date(c.get("last_active", str(now)))
        days_silent = (now - last).days
        recency_scores.append(min(100, days_silent * 1.5))

    avg_recency = sum(recency_scores) / len(recency_scores) if recency_scores else 50.0

    return round(bus_factor_score * 0.5 + avg_recency * 0.5, 1)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return datetime.utcnow().date()


def _risk_label(score: float) -> str:
    if score >= 75:
        return "Critical"
    elif score >= 55:
        return "High"
    elif score >= 35:
        return "Medium"
    elif score >= 15:
        return "Low"
    return "Healthy"


def _risk_color(score: float) -> str:
    if score >= 75:
        return "#E53935"
    elif score >= 55:
        return "#FB8C00"
    elif score >= 35:
        return "#FDD835"
    elif score >= 15:
        return "#43A047"
    return "#00897B"


def _identify_bottlenecks(scores: dict) -> List[dict]:
    """Return the top risk dimensions with human-readable explanations."""
    labels = {
        "commit_decay":    "Commit velocity is declining sharply",
        "pr_stagnation":   "Pull requests are stale with no review activity",
        "issue_backlog":   "Critical issues are accumulating unresolved",
        "contributor_disengagement": "Key contributors are going silent",
        "sentiment_risk":  "Team communication shows stress or disengagement",
    }
    bottlenecks = [
        {"dimension": k, "score": v, "message": labels[k]}
        for k, v in scores.items() if v >= 50
    ]
    return sorted(bottlenecks, key=lambda x: -x["score"])


def _estimate_trend(commits: List[dict]) -> str:
    """Simple linear trend on recent commit counts."""
    if len(commits) < 4:
        return "insufficient data"
    recent = [c["count"] for c in commits[-6:]]
    slope = sum((i - len(recent) / 2) * v for i, v in enumerate(recent))
    if slope > 2:
        return "improving"
    elif slope < -2:
        return "declining"
    return "stable"
