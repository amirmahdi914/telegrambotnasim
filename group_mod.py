"""مدیریت گروه: حذف اسپم و فحش، سه اخطار، بعد اخراج."""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from telegram import Update
from telegram.ext import ContextTypes

from config import SPAM_MAX_MESSAGES, SPAM_WINDOW_SECONDS, WARN_LIMIT
from database import add_warning

# لیست کوتاه کلمات نامناسب برای حذف پیام
BAD_WORDS = {
    "کیر",
    "کس",
    "کون",
    "جنده",
    "کونی",
    "لاشی",
    "حرامزاده",
    "مادرجنده",
    "fuck",
    "shit",
}

_recent: dict[tuple[int, int], deque[float]] = defaultdict(deque)
_dupes: dict[tuple[int, int], deque[str]] = defaultdict(deque)


def _contains_bad_word(text: str) -> bool:
    lowered = text.lower()
    tokens = set(re.findall(r"[^\s\W]+", lowered, flags=re.UNICODE))
    compact = re.sub(r"\s+", "", lowered)
    for word in BAD_WORDS:
        if len(word) <= 3:
            if word in tokens:
                return True
        elif word in lowered or word in compact:
            return True
    return False


def _is_spam(chat_id: int, user_id: int, text: str) -> bool:
    now = time.time()
    key = (chat_id, user_id)
    times = _recent[key]
    times.append(now)
    while times and now - times[0] > SPAM_WINDOW_SECONDS:
        times.popleft()
    if len(times) >= SPAM_MAX_MESSAGES:
        return True

    copies = _dupes[key]
    copies.append(text.strip().lower())
    while len(copies) > 4:
        copies.popleft()
    if len(copies) >= 3 and len(set(copies)) == 1 and copies[0]:
        return True
    return False


async def moderate_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user:
        return
    if chat.type not in ("group", "supergroup"):
        return
    if user.is_bot:
        return

    text = message.text or message.caption or ""
    reason = None
    if text and _contains_bad_word(text):
        reason = "محتوای نامناسب"
    elif text and _is_spam(chat.id, user.id, text):
        reason = "اسپم"

    if not reason:
        return

    try:
        await message.delete()
    except Exception:
        pass

    count = add_warning(chat.id, user.id)
    remain = WARN_LIMIT - count
    try:
        if remain > 0:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"{user.full_name} پیام شما به خاطر {reason} حذف شد. "
                    f"اخطار {count} از {WARN_LIMIT}."
                ),
            )
        else:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id)
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"{user.full_name} بعد از {WARN_LIMIT} اخطار از گروه حذف شد.",
            )
    except Exception:
        owner = context.application.bot_data.get("owner_id")
        if owner:
            await context.bot.send_message(
                chat_id=owner,
                text=(
                    "بات نتوانست در گروه عمل کند. "
                    "بات را ادمین کنید و دسترسی حذف پیام و مسدود کردن عضو را بدهید."
                ),
            )
