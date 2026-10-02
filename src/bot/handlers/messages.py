"""Message handler — anti-spam, FAQ auto-response, sentiment logging."""

from __future__ import annotations

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.types import ChatPermissions
from html import escape

from bot.db import Database
from bot.services.antispam import AntiSpamService
from bot.services.faq import find_matching_faq
from bot.services.sentiment import score_sentiment

router = Router()


def setup(bot: Bot, db: Database, antispam: AntiSpamService):
    """Configure message handler."""

    @router.message()
    async def on_message(message: Message):
        """Process every group message."""
        if not message.text or message.chat.type not in ("group", "supergroup") or not message.from_user or message.sender_chat:
            return

        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text

        # 1. Anti-spam check
        settings = await db.get_settings(chat_id)
        result = antispam.check_message(user_id, text, chat_id) if settings.get("antispam_enabled", True) else None
        if result and result.is_spam:
            try:
                await message.delete()
            except Exception:
                pass

            if result.reason in ("scam_link", "scam_keyword"):
                # Auto-mute for scam
                await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                await db.get_or_create_user(user_id, message.from_user.username)
                await db.set_muted(user_id, True, chat_id)
                await bot.send_message(
                    chat_id,
                    f"🚫 User {escape(message.from_user.full_name)} muted for spam ({result.reason}).",
                )
            return

        # 2. Sentiment logging
        sentiment = score_sentiment(text)
        await db.log_message(chat_id, user_id, sentiment)

        # 3. FAQ auto-response
        if not text.startswith("/"):
            faqs = await db.get_faqs(chat_id)
            match = find_matching_faq(text, faqs)
            if match:
                await message.reply(match["response"])

    return router
