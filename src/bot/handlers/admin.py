"""Admin command handlers — /warn /ban /mute /faq /settings /sentiment."""

from __future__ import annotations

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from bot.db import Database
from bot.services.faq import format_faq_list
from bot.services.sentiment import format_sentiment_report
from bot.services.raid import RaidDetector

router = Router()


def setup(bot: Bot, db: Database, admin_ids: list[int], raid: RaidDetector):
    """Configure admin handlers."""

    def is_admin(message: Message) -> bool:
        return message.from_user.id in admin_ids

    @router.message(Command("warn"))
    async def cmd_warn(message: Message):
        if not is_admin(message):
            return

        if not message.reply_to_message:
            await message.reply("Reply to a message to warn the user.")
            return

        target = message.reply_to_message.from_user
        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "No reason"

        warn_count = await db.add_warn(target.id, message.from_user.id, reason)
        await message.reply(
            f"⚠️ {target.full_name} warned ({warn_count}/3).\nReason: {reason}"
        )

        if warn_count >= 3:
            await db.set_banned(target.id, True)
            await bot.ban_chat_member(message.chat.id, target.id)
            await message.reply(f"🚫 {target.full_name} banned (3 warnings).")

    @router.message(Command("ban"))
    async def cmd_ban(message: Message):
        if not is_admin(message):
            return

        if not message.reply_to_message:
            await message.reply("Reply to a message to ban the user.")
            return

        target = message.reply_to_message.from_user
        await db.set_banned(target.id, True)
        await bot.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"🚫 {target.full_name} banned.")

    @router.message(Command("mute"))
    async def cmd_mute(message: Message):
        if not is_admin(message):
            return

        if not message.reply_to_message:
            await message.reply("Reply to a message to mute the user.")
            return

        target = message.reply_to_message.from_user
        from aiogram.types import ChatPermissions

        await db.set_muted(target.id, True)
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await message.reply(f"🔇 {target.full_name} muted.")

    @router.message(Command("unmute"))
    async def cmd_unmute(message: Message):
        if not is_admin(message):
            return

        if not message.reply_to_message:
            await message.reply("Reply to a message to unmute the user.")
            return

        target = message.reply_to_message.from_user
        from aiogram.types import ChatPermissions

        await db.set_muted(target.id, False)
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
            ),
        )
        await message.reply(f"🔊 {target.full_name} unmuted.")

    @router.message(Command("faq"))
    async def cmd_faq(message: Message):
        if not is_admin(message):
            return

        parts = message.text.split(maxsplit=2)

        if len(parts) == 1:
            # List FAQs
            entries = await db.get_faqs(message.chat.id)
            await message.reply(format_faq_list(entries), parse_mode="HTML")
            return

        action = parts[1].lower()

        if action == "add" and len(parts) > 2:
            # /faq add keywords | response
            content = parts[2]
            if "|" not in content:
                await message.reply("Usage: /faq add keyword1,keyword2 | Response text")
                return
            keywords, response = content.split("|", 1)
            faq_id = await db.add_faq(
                message.chat.id,
                keywords.strip(),
                response.strip(),
                message.from_user.id,
            )
            await message.reply(f"✅ FAQ #{faq_id} added.")

        elif action == "del" and len(parts) > 2:
            faq_id = int(parts[2])
            await db.delete_faq(faq_id)
            await message.reply(f"🗑️ FAQ #{faq_id} deleted.")

        else:
            await message.reply(
                "Usage:\n"
                "/faq — list entries\n"
                "/faq add keywords | response\n"
                "/faq del <id>"
            )

    @router.message(Command("sentiment"))
    async def cmd_sentiment(message: Message):
        if not is_admin(message):
            return

        parts = message.text.split()
        hours = int(parts[1]) if len(parts) > 1 else 24

        avg = await db.get_sentiment_avg(message.chat.id, hours)
        report = format_sentiment_report(avg, hours)
        await message.reply(report, parse_mode="HTML")

    @router.message(Command("raid"))
    async def cmd_raid(message: Message):
        if not is_admin(message):
            return

        parts = message.text.split()
        if len(parts) > 1 and parts[1] == "unlock":
            raid.unlock(message.chat.id)
            await message.reply("🔓 Raid lockdown lifted.")
        else:
            status = raid.get_status(message.chat.id)
            if status.is_locked:
                await message.reply(
                    f"🔒 Chat is in lockdown mode.\n"
                    f"Use /raid unlock to lift."
                )
            else:
                await message.reply(
                    f"✅ No active raid.\n"
                    f"Recent joins (1 min): {status.recent_joins}/{raid.threshold}"
                )

    return router
