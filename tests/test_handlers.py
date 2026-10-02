from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Router
from aiogram.types import ChatPermissions

from bot.db import Database
from bot.handlers import admin, join, messages
from bot.services.antispam import AntiSpamService
from bot.services.captcha import CaptchaService
from bot.services.faq import find_matching_faq
from bot.services.raid import RaidDetector


@pytest.mark.asyncio
async def test_warnings_and_faq_deletion_are_chat_scoped(tmp_path):
    db = Database(str(tmp_path / "bot.db"))
    await db.connect()
    try:
        assert await db.add_warn(1, 9, "first", -10) == 1
        assert await db.add_warn(1, 9, "second", -10) == 2
        assert await db.add_warn(1, 9, "different chat", -20) == 1
        faq = await db.add_faq(-10, "rules", "hello", 9)
        await db.delete_faq(faq, -20)
        assert len(await db.get_faqs(-10)) == 1
        await db.delete_faq(faq, -10)
        assert await db.get_faqs(-10) == []
    finally:
        await db.close()


def test_antispam_tracking_is_chat_scoped():
    service = AntiSpamService(rate_limit=1)
    assert not service.check_message(1, "hello", -10).is_spam
    assert not service.check_message(1, "hello", -20).is_spam
    assert service.check_message(1, "again", -10).reason == "flood"


def test_canonical_domains_and_empty_faq_keywords():
    service = AntiSpamService()
    assert not service.check_message(1, "https://binance.com").is_spam
    assert service.check_message(1, "https://binance-reward.com").is_spam
    assert find_matching_faq("hello", [{"keywords": " , ", "response": "wrong"}]) is None


@pytest.mark.asyncio
async def test_permission_update_is_not_new_join(monkeypatch):
    monkeypatch.setattr(join, "router", Router())
    bot = SimpleNamespace(ban_chat_member=AsyncMock(), restrict_chat_member=AsyncMock())
    db = SimpleNamespace(get_settings=AsyncMock())
    router = join.setup(bot, db, CaptchaService(), RaidDetector(), SimpleNamespace())
    event = SimpleNamespace(old_chat_member=SimpleNamespace(status="member"), new_chat_member=SimpleNamespace(status="restricted", is_member=True))
    await router.chat_member.handlers[0].callback(event)
    db.get_settings.assert_not_awaited()
    bot.restrict_chat_member.assert_not_awaited()


@pytest.mark.asyncio
async def test_math_captcha_has_question_and_multiple_choices(monkeypatch):
    monkeypatch.setattr(join, "router", Router())
    monkeypatch.setattr(join.asyncio, "create_task", lambda coro: coro.close())
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(), send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)))
    db = SimpleNamespace(get_settings=AsyncMock(return_value={"captcha_enabled": True}), get_or_create_user=AsyncMock())
    service = CaptchaService(captcha_type="math")
    router = join.setup(bot, db, service, RaidDetector(), SimpleNamespace(welcome_delete_after=60, captcha_timeout=120))
    user = SimpleNamespace(id=1, username="test", full_name="Test")
    event = SimpleNamespace(old_chat_member=SimpleNamespace(status="left"), new_chat_member=SimpleNamespace(status="member", user=user), chat=SimpleNamespace(id=-10, title="Test"))
    await router.chat_member.handlers[0].callback(event)
    sent = bot.send_message.await_args
    assert "Solve:" in sent.args[1]
    assert len(sent.kwargs["reply_markup"].inline_keyboard[0]) == 3


@pytest.mark.asyncio
async def test_scam_mute_reaches_telegram_and_escapes_name(monkeypatch):
    monkeypatch.setattr(messages, "router", Router())
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(), send_message=AsyncMock())
    db = SimpleNamespace(get_settings=AsyncMock(return_value={}), get_or_create_user=AsyncMock(), set_muted=AsyncMock())
    router = messages.setup(bot, db, AntiSpamService())
    message = SimpleNamespace(text="free airdrop", chat=SimpleNamespace(id=-10, type="supergroup"), from_user=SimpleNamespace(id=1, username="test", full_name="<bad>"), sender_chat=None, delete=AsyncMock())
    await router.message.handlers[0].callback(message)
    bot.restrict_chat_member.assert_awaited_once()
    assert bot.restrict_chat_member.await_args.kwargs["permissions"].can_send_messages is False
    db.set_muted.assert_awaited_once_with(1, True, -10)
    assert "&lt;bad&gt;" in bot.send_message.await_args.args[1]


@pytest.mark.asyncio
async def test_unmute_restores_chat_defaults(monkeypatch):
    monkeypatch.setattr(admin, "router", Router())
    permissions = ChatPermissions(can_send_messages=True, can_send_photos=False)
    bot = SimpleNamespace(get_chat=AsyncMock(return_value=SimpleNamespace(permissions=permissions)), restrict_chat_member=AsyncMock())
    db = SimpleNamespace(set_muted=AsyncMock())
    router = admin.setup(bot, db, [9], RaidDetector())
    message = SimpleNamespace(text="/unmute", chat=SimpleNamespace(id=-10, type="supergroup"), from_user=SimpleNamespace(id=9), sender_chat=None, reply_to_message=SimpleNamespace(from_user=SimpleNamespace(id=1, full_name="Test"), sender_chat=None), reply=AsyncMock())
    await router.message.handlers[3].callback(message)
    assert bot.restrict_chat_member.await_args.kwargs["permissions"] == permissions
    db.set_muted.assert_awaited_once_with(1, False, -10)
