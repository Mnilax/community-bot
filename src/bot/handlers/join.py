"""Handler for new member joins — captcha + welcome flow."""

from __future__ import annotations

import asyncio

from aiogram import Router, Bot
from aiogram.types import (
    ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ChatPermissions,
)

from bot.db import Database
from bot.services.captcha import CaptchaService
from bot.services.raid import RaidDetector
from bot.services.welcome import format_welcome

router = Router()


def setup(bot: Bot, db: Database, captcha: CaptchaService, raid: RaidDetector, config):
    """Configure join handler with dependencies."""

    @router.chat_member()
    async def on_member_join(event: ChatMemberUpdated):
        """Handle new members joining."""
        if event.new_chat_member.status not in ("member", "restricted"):
            return

        user = event.new_chat_member.user
        chat_id = event.chat.id

        # Record join for raid detection
        is_raid = raid.record_join(chat_id)
        if is_raid and raid.is_locked(chat_id):
            # During raid — kick immediately
            await bot.ban_chat_member(chat_id, user.id)
            await bot.unban_chat_member(chat_id, user.id)  # Remove ban, just kick
            return

        # Create user in DB
        await db.get_or_create_user(user.id, user.username)

        # Get chat settings
        settings = await db.get_settings(chat_id)

        # Restrict until captcha passed
        if settings.get("captcha_enabled", True):
            await bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )

            challenge = captcha.create_challenge(user.id, chat_id)

            # Send welcome + captcha
            welcome_text = format_welcome(
                username=user.full_name,
                chat_title=event.chat.title or "this group",
                welcome_text=settings.get("welcome_message", "Welcome!"),
                rules_text=settings.get("rules_text", "Be respectful."),
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ I'm not a bot",
                    callback_data=f"captcha:{challenge.answer}",
                )
            ]])

            msg = await bot.send_message(
                chat_id, welcome_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            # Auto-delete welcome after timeout
            asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, config.welcome_delete_after))
        else:
            # Just welcome, no captcha
            welcome_text = format_welcome(
                username=user.full_name,
                chat_title=event.chat.title or "this group",
                welcome_text=settings.get("welcome_message", "Welcome!"),
                rules_text=settings.get("rules_text", "Be respectful."),
            )
            msg = await bot.send_message(chat_id, welcome_text, parse_mode="HTML")
            asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, config.welcome_delete_after))

    @router.callback_query(lambda c: c.data and c.data.startswith("captcha:"))
    async def on_captcha_answer(callback: CallbackQuery):
        """Handle captcha button press."""
        answer = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        if captcha.verify(user_id, chat_id, answer):
            await db.set_captcha_passed(user_id)
            await bot.restrict_chat_member(
                chat_id, user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            await callback.answer("✅ Verified! You can now chat.")
            try:
                await callback.message.delete()
            except Exception:
                pass
        else:
            await callback.answer("❌ Verification failed. Try again.", show_alert=True)

    return router


async def _auto_delete(bot: Bot, chat_id: int, message_id: int, delay: int):
    """Delete a message after a delay."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass
