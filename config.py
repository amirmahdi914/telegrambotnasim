"""تنظیمات بات از فایل .env یا متغیرهای محیطی خوانده می‌شود."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "").strip()

JOB_CHECK_INTERVAL_HOURS = float(os.getenv("JOB_CHECK_INTERVAL_HOURS", "3"))
DAILY_PRICE_REPORT_HOUR = int(os.getenv("DAILY_PRICE_REPORT_HOUR", "9"))
JOB_KEYWORDS = [
    kw.strip()
    for kw in os.getenv(
        "JOB_KEYWORDS", "طراحی سایت,طراحی وب,وب سایت,فرانت‌اند,React"
    ).split(",")
    if kw.strip()
]
STATE_FILE = os.getenv("STATE_FILE", "bot_state.json")
DATABASE_FILE = os.getenv("DATABASE_FILE", "bot_data.db")

# برای تشخیص آهنگ از audd.io یک کلید رایگان بگیرید
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "").strip()

WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))
SPAM_WINDOW_SECONDS = int(os.getenv("SPAM_WINDOW_SECONDS", "12"))
SPAM_MAX_MESSAGES = int(os.getenv("SPAM_MAX_MESSAGES", "7"))


def owner_id() -> int | None:
    if not OWNER_CHAT_ID:
        return None
    try:
        return int(OWNER_CHAT_ID)
    except ValueError:
        return None
