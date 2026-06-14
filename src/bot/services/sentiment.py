"""Simple sentiment scoring for chat messages.

Uses a keyword-based approach (no ML dependencies) to provide
a rough sentiment indicator for community managers.
"""

from __future__ import annotations

POSITIVE_WORDS = {
    "great", "awesome", "love", "good", "nice", "excellent", "amazing",
    "thank", "thanks", "perfect", "wonderful", "happy", "best", "moon",
    "bullish", "pump", "rocket", "gem", "launch", "exciting",
    "congratulations", "congrats", "cool", "wow", "incredible",
}

NEGATIVE_WORDS = {
    "scam", "rug", "dump", "bad", "hate", "terrible", "worst",
    "angry", "frustrated", "disappointed", "bearish", "crash",
    "fake", "shit", "dead", "dying", "useless", "garbage",
    "waste", "awful", "horrible", "fear", "panic", "sell",
}


def score_sentiment(text: str) -> float:
    """Score message sentiment from -1.0 (negative) to +1.0 (positive).

    Uses simple keyword matching. Returns 0.0 for neutral.
    """
    words = set(text.lower().split())

    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)

    total = positive_count + negative_count
    if total == 0:
        return 0.0

    return (positive_count - negative_count) / total


def sentiment_label(score: float) -> str:
    """Human-readable label for a sentiment score."""
    if score >= 0.3:
        return "🟢 Positive"
    if score <= -0.3:
        return "🔴 Negative"
    return "🟡 Neutral"


def format_sentiment_report(avg_score: float, period_hours: int = 24) -> str:
    """Format a sentiment report for admins."""
    label = sentiment_label(avg_score)
    return (
        f"📊 <b>Chat Sentiment Report</b> (last {period_hours}h)\n\n"
        f"Average score: {avg_score:+.2f}\n"
        f"Mood: {label}"
    )
