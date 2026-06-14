"""Anti-spam service — scam links, flood detection, duplicate messages."""

from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field

# Common crypto scam URL patterns
SCAM_PATTERNS = [
    r"(?:https?://)?(?:www\.)?(?:airdrop|claim|free-?token|giveaway|reward)[a-z0-9\-]*\.(?:com|org|net|io|xyz)",
    r"(?:https?://)?[a-z0-9\-]+\.(?:com|org|net|io|xyz)/(?:airdrop|claim|free|giveaway|reward)",
    r"(?:https?://)?t\.me/[a-z0-9_]+bot\?start=",  # Suspicious bot referrals
    r"(?:https?://)?(?:www\.)?(?:binance|coinbase|metamask)[a-z\-]*\.(?:com|org|net)(?!/)",  # Phishing clones
]

SCAM_KEYWORDS = [
    "free airdrop", "claim your tokens", "connect wallet", "verify wallet",
    "guaranteed profit", "100x gem", "send eth to receive",
]


@dataclass
class FloodTracker:
    """Sliding window flood detection per user."""

    timestamps: list[float] = field(default_factory=list)


@dataclass
class SpamResult:
    """Result of spam check."""

    is_spam: bool = False
    reason: str = ""


class AntiSpamService:
    """Anti-spam detection engine."""

    def __init__(self, rate_limit: int = 5, window_seconds: int = 10):
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self._flood_trackers: dict[int, FloodTracker] = defaultdict(FloodTracker)
        self._recent_hashes: dict[int, list[str]] = defaultdict(list)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in SCAM_PATTERNS]

    def check_message(self, user_id: int, text: str) -> SpamResult:
        """Run all anti-spam checks on a message.

        Args:
            user_id: Telegram user ID
            text: Message text

        Returns:
            SpamResult with is_spam flag and reason
        """
        # 1. Scam link check
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return SpamResult(is_spam=True, reason="scam_link")

        # 2. Scam keywords
        text_lower = text.lower()
        for keyword in SCAM_KEYWORDS:
            if keyword in text_lower:
                return SpamResult(is_spam=True, reason="scam_keyword")

        # 3. Flood check (sliding window)
        now = time.time()
        tracker = self._flood_trackers[user_id]
        tracker.timestamps = [t for t in tracker.timestamps if now - t < self.window_seconds]
        tracker.timestamps.append(now)

        if len(tracker.timestamps) > self.rate_limit:
            return SpamResult(is_spam=True, reason="flood")

        # 4. Duplicate message check
        msg_hash = hashlib.md5(text.encode()).hexdigest()
        recent = self._recent_hashes[user_id]
        if msg_hash in recent[-5:]:  # Last 5 messages
            return SpamResult(is_spam=True, reason="duplicate")
        recent.append(msg_hash)
        if len(recent) > 20:
            self._recent_hashes[user_id] = recent[-10:]

        return SpamResult(is_spam=False)

    def reset_user(self, user_id: int) -> None:
        """Reset tracking for a user."""
        self._flood_trackers.pop(user_id, None)
        self._recent_hashes.pop(user_id, None)
