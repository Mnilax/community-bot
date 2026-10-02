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


def _is_member(member) -> bool:
    return member.status in ("member", "administrator", "creator") or (
        member.status == "restricted" and member.is_member
    )


def setup(bot: Bot, db: Database, captcha: CaptchaService, raid: RaidDetector, config):
    """Configure join handler with dependencies."""

    @router.chat_member()
    async def on_member_join(event: ChatMemberUpdated):
        """Handle new members joining."""
        if _is_member(event.old_chat_member) or not _is_member(event.new_chat_member):
            return

        user = event.new_chat_member.user
        if getattr(user, "is_bot", False):
            return
        chat_id = event.chat.id

        # Record join for raid detection
        settings = await db.get_settings(chat_id)
        is_raid = raid.record_join(chat_id) if settings.get("raid_protection", True) else False
        if is_raid and raid.is_locked(chat_id):
            # During raid — kick immediately
            await bot.ban_chat_member(chat_id, user.id)
            await bot.unban_chat_member(chat_id, user.id)  # Remove ban, just kick
            return

        # Create user in DB
        await db.get_or_create_user(user.id, user.username)

        # Get chat settings
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

            if captcha.captcha_type == "math":
                welcome_text += f"\n\nSolve: <b>{challenge.question}</b>"
                choices = [int(challenge.answer) - 1, int(challenge.answer), int(challenge.answer) + 1]
                import random
                random.shuffle(choices)
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=str(value), callback_data=f"captcha:{value}") for value in choices
                ]])
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ I'm not a bot", callback_data=f"captcha:{challenge.answer}")
                ]])

            msg = await bot.send_message(
                chat_id, welcome_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            # Auto-delete welcome after timeout
            asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, max(config.welcome_delete_after, config.captcha_timeout)))
        else:
            # Just welcome, no captcha
            welcome_text = format_welcome(
                username=user.full_name,
                chat_title=event.chat.title or "this group",
                welcome_text=settings.get("welcome_message", "Welcome!"),
                rules_text=settings.get("rules_text", "Be respectful."),
                verification_required=False,
            )
            msg = await bot.send_message(chat_id, welcome_text, parse_mode="HTML")
            asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, config.welcome_delete_after))

    @router.callback_query(lambda c: c.data and c.data.startswith("captcha:"))
    async def on_captcha_answer(callback: CallbackQuery):
        """Handle captcha button press."""
        if callback.message is None:
            await callback.answer("Verification message is unavailable.", show_alert=True)
            return
        answer = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        if captcha.verify(user_id, chat_id, answer, consume=False):
            chat = await bot.get_chat(chat_id)
            await bot.restrict_chat_member(
                chat_id, user_id,
                permissions=chat.permissions or ChatPermissions(can_send_messages=True),
            )
            captcha.verify(user_id, chat_id, answer)
            await db.set_captcha_passed(user_id)
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
