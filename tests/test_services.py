"""Tests for bot services — pure function tests (no Telegram API)."""

from bot.services.antispam import AntiSpamService
from bot.services.captcha import CaptchaService
from bot.services.faq import find_matching_faq
from bot.services.raid import RaidDetector
from bot.services.sentiment import score_sentiment, sentiment_label
from bot.services.welcome import format_welcome


# --- AntiSpam ---

def test_scam_link_detected():
    svc = AntiSpamService()
    result = svc.check_message(1, "Check out https://free-token-airdrop.com/claim")
    assert result.is_spam
    assert result.reason == "scam_link"

def test_scam_keyword_detected():
    svc = AntiSpamService()
    result = svc.check_message(1, "free airdrop for everyone!")
    assert result.is_spam
    assert result.reason == "scam_keyword"

def test_clean_message():
    svc = AntiSpamService()
    result = svc.check_message(1, "Hello, what is the roadmap?")
    assert not result.is_spam

def test_flood_detection():
    svc = AntiSpamService(rate_limit=3, window_seconds=60)
    for i in range(3):
        result = svc.check_message(1, f"message {i}")
        assert not result.is_spam
    result = svc.check_message(1, "one more")
    assert result.is_spam
    assert result.reason == "flood"

def test_duplicate_detection():
    svc = AntiSpamService()
    svc.check_message(1, "buy now!")
    result = svc.check_message(1, "buy now!")
    assert result.is_spam
    assert result.reason == "duplicate"


# --- Captcha ---

def test_captcha_verify():
    svc = CaptchaService(timeout=60, captcha_type="button")
    challenge = svc.create_challenge(user_id=1, chat_id=100)
    assert svc.is_pending(1, 100)
    assert svc.verify(1, 100, challenge.answer)
    assert not svc.is_pending(1, 100)

def test_captcha_wrong_answer():
    svc = CaptchaService(timeout=60)
    svc.create_challenge(user_id=1, chat_id=100)
    assert not svc.verify(1, 100, "wrong_answer")
    assert svc.is_pending(1, 100)


# --- FAQ ---

def test_faq_matching():
    entries = [
        {"id": 1, "keywords": "roadmap, plan", "response": "Check our website."},
        {"id": 2, "keywords": "token, price", "response": "See CoinGecko."},
    ]
    match = find_matching_faq("what is the roadmap?", entries)
    assert match["id"] == 1

    match = find_matching_faq("when token launch?", entries)
    assert match["id"] == 2

    match = find_matching_faq("hello everyone", entries)
    assert match is None


# --- Raid ---

def test_raid_detection():
    detector = RaidDetector(threshold=3, lockdown_minutes=1)
    assert not detector.record_join(100)
    assert not detector.record_join(100)
    assert detector.record_join(100)  # 3rd join triggers lockdown
    assert detector.is_locked(100)

def test_raid_unlock():
    detector = RaidDetector(threshold=2, lockdown_minutes=1)
    detector.record_join(100)
    detector.record_join(100)
    assert detector.is_locked(100)
    detector.unlock(100)
    assert not detector.is_locked(100)


# --- Sentiment ---

def test_positive_sentiment():
    score = score_sentiment("This is awesome and great!")
    assert score > 0

def test_negative_sentiment():
    score = score_sentiment("This is a scam, terrible dump")
    assert score < 0

def test_neutral_sentiment():
    score = score_sentiment("Hello how are you")
    assert score == 0.0

def test_sentiment_label():
    assert "Positive" in sentiment_label(0.5)
    assert "Negative" in sentiment_label(-0.5)
    assert "Neutral" in sentiment_label(0.0)


# --- Welcome ---

def test_welcome_format():
    result = format_welcome("Alice", "Test Group", "Welcome!", "Be nice.")
    assert "Alice" in result
    assert "Welcome!" in result
    assert "Be nice." in result

def test_welcome_escapes_html():
    result = format_welcome("<script>alert</script>", "Test", "Hi", "Rules")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
