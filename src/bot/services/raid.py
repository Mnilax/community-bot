"""Raid detection — tracks join spikes and triggers lockdown."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RaidStatus:
    """Current raid detection status for a chat."""

    is_locked: bool = False
    lockdown_until: float = 0.0
    recent_joins: int = 0


class RaidDetector:
    """Detect and respond to join raids.

    Tracks join events per chat in a 60-second sliding window.
    When joins exceed the threshold, triggers a lockdown.
    """

    def __init__(self, threshold: int = 10, lockdown_minutes: int = 5):
        self.threshold = threshold
        self.lockdown_minutes = lockdown_minutes
        self._join_times: dict[int, list[float]] = defaultdict(list)
        self._lockdowns: dict[int, float] = {}

    def record_join(self, chat_id: int) -> bool:
        """Record a join event. Returns True if raid is detected.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if this join triggered or continues a raid lockdown
        """
        now = time.time()

        # Check existing lockdown
        if self.is_locked(chat_id):
            return True

        # Record join
        self._join_times[chat_id].append(now)

        # Clean old entries (1-minute window)
        self._join_times[chat_id] = [
            t for t in self._join_times[chat_id] if now - t < 60
        ]

        # Check threshold
        if len(self._join_times[chat_id]) >= self.threshold:
            self._lockdowns[chat_id] = now + (self.lockdown_minutes * 60)
            self._join_times[chat_id].clear()
            return True

        return False

    def is_locked(self, chat_id: int) -> bool:
        """Check if a chat is in lockdown."""
        lockdown_until = self._lockdowns.get(chat_id, 0)
        if time.time() < lockdown_until:
            return True
        if chat_id in self._lockdowns:
            del self._lockdowns[chat_id]
        return False

    def get_status(self, chat_id: int) -> RaidStatus:
        """Get raid status for a chat."""
        now = time.time()
        recent = [t for t in self._join_times.get(chat_id, []) if now - t < 60]
        locked = self.is_locked(chat_id)

        return RaidStatus(
            is_locked=locked,
            lockdown_until=self._lockdowns.get(chat_id, 0),
            recent_joins=len(recent),
        )

    def unlock(self, chat_id: int) -> None:
        """Manually end lockdown."""
        self._lockdowns.pop(chat_id, None)
