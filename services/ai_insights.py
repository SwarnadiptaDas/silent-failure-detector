import os

from groq import Groq
import json
from typing import Dict


def generate_insights(risk_result: dict, sentiment_result: dict, repo_data: dict) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = _build_prompt(risk_result, sentiment_result, repo_data)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )

    return response.choices[0].message.content


def generate_insights_streaming(risk_result: dict, sentiment_result: dict, repo_data: dict):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = _build_prompt(risk_result, sentiment_result, repo_data)

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _build_prompt(risk_result: dict, sentiment_result: dict, repo_data: dict) -> str:
    repo_name   = repo_data.get("repo", {}).get("name", "this repository")
    overall     = risk_result.get("overall", 0)
    label       = risk_result.get("label", "Unknown")
    dimensions  = risk_result.get("dimensions", {})
    bottlenecks = risk_result.get("bottlenecks", [])
    trend       = risk_result.get("trend", "unknown")
    sentiment_label = sentiment_result.get("sentiment_label", "neutral")
    neg_signals = sentiment_result.get("negative_signal_count", 0)

    return f"""You are an expert software engineering coach analysing project health signals.

Project: {repo_name}
Overall Risk Score: {overall}/100 ({label})
Trend: {trend}

Risk Dimensions (0-100, higher = more risk):
- Commit velocity decay: {dimensions.get('commit_decay', 'N/A')}
- PR stagnation: {dimensions.get('pr_stagnation', 'N/A')}
- Issue backlog health: {dimensions.get('issue_backlog', 'N/A')}
- Contributor disengagement: {dimensions.get('contributor_disengagement', 'N/A')}
- Sentiment / communication risk: {dimensions.get('sentiment_risk', 'N/A')}

Top bottlenecks identified:
{json.dumps(bottlenecks, indent=2)}

Communication sentiment: {sentiment_label} ({neg_signals} negative stress signals detected)

Based on these signals, provide:
1. A 2-sentence executive summary of what is happening in this project
2. The top 3 specific, actionable recommendations to reduce failure risk
3. One early warning — something subtle that teams usually miss at this risk level

Be direct, concrete, and practical. Avoid generic advice. Format your response clearly with these three sections. Keep the total response under 280 words."""