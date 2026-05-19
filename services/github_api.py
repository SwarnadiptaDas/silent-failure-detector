import requests
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

GITHUB_API_BASE = "https://api.github.com"


def get_headers(token: str = None) -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def fetch_repo_data(owner: str, repo: str, token: str = None) -> dict:
    """Fetch comprehensive repository data from GitHub API."""
    headers = get_headers(token)
    base_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

    try:
        # Core repo info
        repo_resp = requests.get(base_url, headers=headers, timeout=10)
        repo_resp.raise_for_status()
        repo_info = repo_resp.json()

        # Commits (last 90 days)
        since = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
        commits_resp = requests.get(
            f"{base_url}/commits",
            headers=headers,
            params={"since": since, "per_page": 100},
            timeout=10,
        )
        raw_commits = commits_resp.json() if commits_resp.ok else []

        # Pull requests
        prs_resp = requests.get(
            f"{base_url}/pulls",
            headers=headers,
            params={"state": "all", "per_page": 50, "sort": "updated"},
            timeout=10,
        )
        pull_requests = prs_resp.json() if prs_resp.ok else []

        # Issues (exclude PRs)
        issues_resp = requests.get(
            f"{base_url}/issues",
            headers=headers,
            params={"state": "all", "per_page": 50, "sort": "updated"},
            timeout=10,
        )
        all_issues = issues_resp.json() if issues_resp.ok else []
        issues = [i for i in all_issues if "pull_request" not in i]

        # Contributors
        contributors_resp = requests.get(
            f"{base_url}/contributors",
            headers=headers,
            params={"per_page": 30},
            timeout=10,
        )
        contributors = contributors_resp.json() if contributors_resp.ok else []

        # PR comments (from open PRs)
        pr_comments = []
        for pr in pull_requests[:10]:
            pr_num = pr.get("number")
            comments_resp = requests.get(
                f"{base_url}/issues/{pr_num}/comments",
                headers=headers,
                timeout=10,
            )
            if comments_resp.ok:
                for c in comments_resp.json():
                    body = c.get("body", "").strip()
                    if body:
                        pr_comments.append(body)

        # Build commit time series
        commit_series = _build_commit_series(raw_commits)

        return {
            "repo": {
                "name": f"{owner}/{repo}",
                "description": repo_info.get("description", ""),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "open_issues": repo_info.get("open_issues_count", 0),
                "created_at": repo_info.get("created_at", ""),
                "updated_at": repo_info.get("updated_at", ""),
            },
            "commits": commit_series,
            "pull_requests": _parse_prs(pull_requests),
            "issues": _parse_issues(issues),
            "contributors": _parse_contributors(contributors),
            "pr_comments": pr_comments,
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def _build_commit_series(raw_commits: list) -> list:
    """Aggregate commits into weekly buckets with author info."""
    daily = defaultdict(lambda: {"count": 0, "author": "unknown"})
    for c in raw_commits:
        try:
            date_str = c["commit"]["author"]["date"][:10]
            author = c.get("author", {})
            login = author.get("login", "unknown") if author else "unknown"
            daily[date_str]["count"] += 1
            daily[date_str]["author"] = login
        except (KeyError, TypeError):
            continue
    return [{"date": d, **v} for d, v in sorted(daily.items())]


def _parse_prs(prs: list) -> list:
    out = []
    for pr in prs:
        try:
            out.append({
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "created_at": pr["created_at"][:10],
                "updated_at": pr["updated_at"][:10],
                "comments": pr.get("comments", 0),
                "author": (pr.get("user") or {}).get("login", "unknown"),
            })
        except (KeyError, TypeError):
            continue
    return out


def _parse_issues(issues: list) -> list:
    out = []
    for issue in issues:
        try:
            out.append({
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "created_at": issue["created_at"][:10],
                "comments": issue.get("comments", 0),
                "labels": [l["name"] for l in issue.get("labels", [])],
            })
        except (KeyError, TypeError):
            continue
    return out


def _parse_contributors(contributors: list) -> list:
    out = []
    for c in contributors:
        try:
            out.append({
                "login": c.get("login", "unknown"),
                "contributions": c.get("contributions", 0),
                "last_active": datetime.utcnow().strftime("%Y-%m-%d"),
            })
        except (KeyError, TypeError):
            continue
    return out


def load_demo_data() -> dict:
    """Load sample data for demo/fallback mode."""
    demo_path = os.path.join(os.path.dirname(__file__), "../data/sample_data.json")
    with open(demo_path, "r") as f:
        return json.load(f)
