"""Welcome flow for new members."""

from __future__ import annotations


def format_welcome(
    username: str,
    chat_title: str,
    welcome_text: str,
    rules_text: str,
    verification_required: bool = True,
) -> str:
    """Format a welcome message for a new member.

    Args:
        username: New member's display name
        chat_title: Chat/group title
        welcome_text: Custom welcome message from settings
        rules_text: Rules text from settings

    Returns:
        Formatted welcome message with Telegram HTML
    """
    return (
        f"👋 <b>Welcome, {_escape_html(username)}!</b>\n\n"
        f"{welcome_text}\n\n"
        f"📋 <b>Rules:</b>\n{rules_text}\n\n"
        + ("Please complete the verification to start chatting." if verification_required else "")
    )


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
