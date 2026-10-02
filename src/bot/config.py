"""Bot configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Bot configuration."""

    bot_token: str = ""
    admin_ids: list[int] = field(default_factory=list)

    # Anti-spam
    flood_rate_limit: int = 5
    flood_window_seconds: int = 10

    # Captcha
    captcha_timeout: int = 120
    captcha_type: str = "button"  # "button" or "math"

    # Welcome
    welcome_delete_after: int = 60

    # Raid detection
    raid_join_threshold: int = 10
    raid_lockdown_minutes: int = 5

    # Database
    database_path: str = "bot.db"


def load_config() -> Config:
    """Load config from environment."""
    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=admin_ids,
        flood_rate_limit=int(os.getenv("FLOOD_RATE_LIMIT", "5")),
        flood_window_seconds=int(os.getenv("FLOOD_WINDOW_SECONDS", "10")),
        captcha_timeout=int(os.getenv("CAPTCHA_TIMEOUT", "120")),
        captcha_type=os.getenv("CAPTCHA_TYPE", "button"),
        welcome_delete_after=int(os.getenv("WELCOME_DELETE_AFTER", "60")),
        raid_join_threshold=int(os.getenv("RAID_JOIN_THRESHOLD", "10")),
        raid_lockdown_minutes=int(os.getenv("RAID_LOCKDOWN_MINUTES", "5")),
        database_path=os.getenv("DATABASE_PATH", "bot.db"),
    )
