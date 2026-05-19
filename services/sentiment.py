from textblob import TextBlob
import re
from typing import List, Dict


# Keyword signals that indicate team stress / disengagement
NEGATIVE_SIGNALS = [
    "nobody", "no one", "stale", "abandoned", "broken", "failing",
    "stuck", "blocked", "conflict", "nobody reviewing", "no review",
    "weeks", "no progress", "not sure", "hacky", "temporary", "workaround",
    "ignore", "skip", "later", "eventually", "TODO", "FIXME",
]

POSITIVE_SIGNALS = [
    "great", "approved", "lgtm", "merged", "resolved", "fixed",
    "done", "shipped", "nice work", "good catch", "thank",
]


def analyze_sentiment(texts: List[str]) -> Dict:
    """
    Analyze sentiment of PR comments / issue text.
    Returns aggregate scores and per-text breakdown.
    """
    if not texts:
        return {
            "average_polarity": 0.0,
            "average_subjectivity": 0.0,
            "sentiment_label": "neutral",
            "negative_signal_count": 0,
            "positive_signal_count": 0,
            "breakdown": [],
            "risk_contribution": 0.0,
        }

    breakdown = []
    polarities = []
    subjectivities = []
    neg_signals = 0
    pos_signals = 0

    for text in texts:
        clean = _clean_text(text)
        blob = TextBlob(clean)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        polarities.append(polarity)
        subjectivities.append(subjectivity)

        # Keyword scan
        lower = clean.lower()
        neg_hits = sum(1 for s in NEGATIVE_SIGNALS if s.lower() in lower)
        pos_hits = sum(1 for s in POSITIVE_SIGNALS if s.lower() in lower)
        neg_signals += neg_hits
        pos_signals += pos_hits

        label = _polarity_label(polarity)
        breakdown.append({
            "text": text[:120] + ("..." if len(text) > 120 else ""),
            "polarity": round(polarity, 3),
            "subjectivity": round(subjectivity, 3),
            "label": label,
            "neg_signals": neg_hits,
        })

    avg_polarity = sum(polarities) / len(polarities)
    avg_subjectivity = sum(subjectivities) / len(subjectivities)

    # Risk contribution: negative polarity + stress keywords = higher risk
    # Normalised to 0–1 range
    polarity_risk = max(0.0, -avg_polarity)               # 0 when neutral/positive
    keyword_risk = min(1.0, neg_signals / max(len(texts), 1) * 0.5)
    risk_contribution = round((polarity_risk * 0.6 + keyword_risk * 0.4), 3)

    return {
        "average_polarity": round(avg_polarity, 3),
        "average_subjectivity": round(avg_subjectivity, 3),
        "sentiment_label": _polarity_label(avg_polarity),
        "negative_signal_count": neg_signals,
        "positive_signal_count": pos_signals,
        "breakdown": breakdown,
        "risk_contribution": risk_contribution,
    }


def _clean_text(text: str) -> str:
    """Remove markdown, code blocks, and URLs."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[#*_~>]", "", text)
    return text.strip()


def _polarity_label(polarity: float) -> str:
    if polarity > 0.15:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    return "neutral"
