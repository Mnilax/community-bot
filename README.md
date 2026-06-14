# Community Management Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

Telegram bot for community moderation and onboarding built with aiogram 3.x. Handles anti-spam, captcha verification, welcome flows, FAQ auto-response, raid detection, and sentiment tracking.

<!-- TODO: replace with real demo GIF/screenshots showing welcome, captcha, and antispam flows -->
![Demo](assets/demo.gif)

## Features

| Feature | Description |
|---------|-------------|
| **Anti-spam** | Scam link blocklist (crypto patterns), sliding-window flood detection, duplicate message detection |
| **Captcha gate** | New members can't chat until passing button/math captcha |
| **Welcome flow** | Customizable welcome message + rules, auto-deletes after timeout |
| **FAQ responder** | Keyword-based auto-responses, admin-configurable via commands |
| **Raid detection** | Join spike monitoring with auto-lockdown + admin alert |
| **Sentiment tracking** | Per-chat mood scoring for community manager reports |
| **Admin commands** | `/warn`, `/ban`, `/mute`, `/unmute`, `/faq`, `/sentiment`, `/raid` |

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Copy `.env.example` to `.env` and fill in your values
3. Install and run:

```bash
pip install -e .
python -m bot.main
```

## Admin Commands

| Command | Description |
|---------|-------------|
| `/warn` | Warn a user (reply to message). 3 warns = auto-ban |
| `/ban` | Ban a user immediately |
| `/mute` | Mute a user (restrict messages) |
| `/unmute` | Unmute a user |
| `/faq` | List FAQ entries |
| `/faq add keywords \| response` | Add FAQ entry |
| `/faq del <id>` | Delete FAQ entry |
| `/sentiment [hours]` | Show chat sentiment report |
| `/raid` | Show raid status |
| `/raid unlock` | Lift raid lockdown |

## Anti-Spam

The bot blocks:
- Known crypto scam URL patterns (airdrop/claim/giveaway sites)
- Scam keywords ("free airdrop", "connect wallet", etc.)
- Message flooding (configurable rate limit per user)
- Duplicate messages

Detected scam posts auto-mute the sender.

## Architecture

```
src/bot/
├── main.py              # Entry point, router registration
├── config.py            # Environment config loader
├── db.py                # SQLite schema + async queries
├── handlers/
│   ├── join.py          # New member → captcha + welcome
│   ├── messages.py      # Anti-spam → sentiment → FAQ
│   └── admin.py         # /warn /ban /mute /faq /sentiment
└── services/
    ├── antispam.py      # Scam detection + flood + dedup
    ├── captcha.py       # Button/math captcha challenges
    ├── welcome.py       # Welcome message formatting
    ├── faq.py           # Keyword matching FAQ engine
    ├── raid.py          # Join spike detection + lockdown
    └── sentiment.py     # Keyword-based mood scoring
```

## Configuration

See `.env.example` for all options. Key settings:

- `BOT_TOKEN` — Telegram bot token
- `ADMIN_IDS` — comma-separated admin user IDs
- `FLOOD_RATE_LIMIT` / `FLOOD_WINDOW_SECONDS` — anti-spam tuning
- `RAID_JOIN_THRESHOLD` — joins/minute to trigger lockdown
- `CAPTCHA_TYPE` — `button` or `math`

## License

MIT
