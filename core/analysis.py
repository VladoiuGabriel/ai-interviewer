import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()
AGREEMENT_THRESHOLD = 0.3


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_quotes(quotes, answers: list[str]) -> tuple[list[str], list[str]]:
    """Split quotes into (found verbatim in an answer, not found)."""
    normalized_answers = [_normalize(a) for a in answers]
    kept, removed = [], []
    for q in quotes or []:
        if not isinstance(q, str):
            continue
        needle = _normalize(q).strip("\"'“”")
        (kept if any(needle in a for a in normalized_answers) else removed).append(q)
    return kept, removed


def local_sentiment(answers: list[str]) -> float:
    """Average VADER compound score (-1..1) across answers."""
    scores = [_vader.polarity_scores(a)["compound"] for a in answers]
    return round(sum(scores) / len(scores), 2) if scores else 0.0


def analyze(answers: list[str], summary: dict, removed_quotes: list[str]) -> dict:
    vader_score = local_sentiment(answers)

    ai_score = None
    sentiment = summary.get("sentiment")
    if isinstance(sentiment, dict):
        try:
            ai_score = float(sentiment.get("score"))
        except (TypeError, ValueError):
            pass

    word_counts = [len(a.split()) for a in answers]
    return {
        "local_sentiment": {
            "method": "VADER (English only)",
            "score": vader_score,
            "agrees_with_ai": None if ai_score is None
            else abs(vader_score - ai_score) <= AGREEMENT_THRESHOLD,
        },
        "quotes_removed": removed_quotes,
        "stats": {
            "answers": len(answers),
            "total_words": sum(word_counts),
            "avg_words_per_answer": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0,
        },
    }