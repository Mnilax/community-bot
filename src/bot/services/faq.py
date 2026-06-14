"""FAQ auto-responder — keyword matching against stored FAQ entries."""

from __future__ import annotations


def find_matching_faq(text: str, faq_entries: list[dict]) -> dict | None:
    """Find the best matching FAQ entry for a message.

    Args:
        text: Incoming message text
        faq_entries: List of FAQ dicts with 'keywords' and 'response'

    Returns:
        Best matching FAQ entry or None
    """
    text_lower = text.lower().strip()

    best_match = None
    best_score = 0

    for entry in faq_entries:
        keywords = [k.strip().lower() for k in entry["keywords"].split(",")]
        score = sum(1 for kw in keywords if kw in text_lower)

        if score > best_score:
            best_score = score
            best_match = entry

    return best_match if best_score > 0 else None


def format_faq_list(entries: list[dict]) -> str:
    """Format FAQ entries for display."""
    if not entries:
        return "No FAQ entries configured."

    lines = ["📚 <b>FAQ Entries:</b>\n"]
    for entry in entries:
        lines.append(f"  #{entry['id']} — <b>{entry['keywords']}</b>\n  → {entry['response']}\n")

    return "\n".join(lines)
