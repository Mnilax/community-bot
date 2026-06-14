"""Captcha service for new member verification."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class CaptchaChallenge:
    """Active captcha challenge."""

    user_id: int
    chat_id: int
    answer: str
    message_id: int | None = None
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


class CaptchaService:
    """Manages captcha challenges for new members."""

    def __init__(self, timeout: int = 120, captcha_type: str = "button"):
        self.timeout = timeout
        self.captcha_type = captcha_type
        self._pending: dict[tuple[int, int], CaptchaChallenge] = {}

    def create_challenge(self, user_id: int, chat_id: int) -> CaptchaChallenge:
        """Create a new captcha challenge."""
        if self.captcha_type == "math":
            a, b = random.randint(1, 20), random.randint(1, 20)
            answer = str(a + b)
            challenge = CaptchaChallenge(user_id=user_id, chat_id=chat_id, answer=answer)
        else:
            # Button captcha — answer is a predefined token
            answer = f"verify_{user_id}"
            challenge = CaptchaChallenge(user_id=user_id, chat_id=chat_id, answer=answer)

        self._pending[(chat_id, user_id)] = challenge
        return challenge

    def verify(self, user_id: int, chat_id: int, answer: str) -> bool:
        """Check if the answer is correct."""
        key = (chat_id, user_id)
        challenge = self._pending.get(key)

        if not challenge:
            return False

        if time.time() - challenge.created_at > self.timeout:
            self._pending.pop(key, None)
            return False

        if answer == challenge.answer:
            self._pending.pop(key, None)
            return True

        return False

    def is_pending(self, user_id: int, chat_id: int) -> bool:
        """Check if user has a pending captcha."""
        key = (chat_id, user_id)
        challenge = self._pending.get(key)
        if not challenge:
            return False
        if time.time() - challenge.created_at > self.timeout:
            self._pending.pop(key, None)
            return False
        return True

    def get_expired(self) -> list[CaptchaChallenge]:
        """Get and remove expired challenges."""
        now = time.time()
        expired = []
        to_remove = []

        for key, challenge in self._pending.items():
            if now - challenge.created_at > self.timeout:
                expired.append(challenge)
                to_remove.append(key)

        for key in to_remove:
            del self._pending[key]

        return expired
