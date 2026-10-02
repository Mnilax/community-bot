from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Router

from bot.handlers import join
from bot.services.captcha import CaptchaService
from bot.services.raid import RaidDetector
from bot.services.welcome import format_welcome


@pytest.mark.asyncio
async def test_failed_unrestriction_keeps_challenge_retryable(monkeypatch):
    monkeypatch.setattr(join, "router", Router())
    service = CaptchaService()
    challenge = service.create_challenge(1, -10)
    bot = SimpleNamespace(get_chat=AsyncMock(side_effect=RuntimeError("temporary Telegram failure")))
    router = join.setup(bot, SimpleNamespace(), service, RaidDetector(), SimpleNamespace())
    callback = SimpleNamespace(data=f"captcha:{challenge.answer}", from_user=SimpleNamespace(id=1), message=SimpleNamespace(chat=SimpleNamespace(id=-10)))
    with pytest.raises(RuntimeError):
        await router.callback_query.handlers[0].callback(callback)
    assert service.is_pending(1, -10)


def test_no_captcha_welcome_does_not_ask_for_verification():
    assert "verification" not in format_welcome("Test", "Group", "Welcome", "Rules", verification_required=False)
