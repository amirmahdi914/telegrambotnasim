"""تشخیص آهنگ از ویس یا فایل صوتی با سرویس AudD (نه دانلود غیرقانونی فایل)."""
from __future__ import annotations

import logging

import requests
from telegram import Update
from telegram.ext import ContextTypes

from config import AUDD_API_KEY

logger = logging.getLogger(__name__)


async def identify_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    audio = message.audio or message.voice or message.video_note
    if not audio:
        return
    if not AUDD_API_KEY:
        await message.reply_text(
            "تشخیص آهنگ آماده است، ولی کلید AudD تنظیم نشده. "
            "در فایل .env مقدار AUDD_API_KEY را از https://audd.io بگذارید."
        )
        return

    await message.reply_text("در حال تشخیص آهنگ...")
    try:
        file = await audio.get_file()
        data = await file.download_as_bytearray()
        resp = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "return": "spotify,apple_music"},
            files={"file": ("audio.mp3", bytes(data))},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        result = payload.get("result")
        if not result:
            await message.reply_text("آهنگی پیدا نشد.")
            return
        title = result.get("title") or "نامشخص"
        artist = result.get("artist") or "نامشخص"
        album = result.get("album") or "-"
        await message.reply_text(
            "🎵 آهنگ پیدا شد\n"
            f"نام: {title}\n"
            f"خواننده: {artist}\n"
            f"آلبوم: {album}\n\n"
            "برای گوش دادن از اسپاتیفای یا منابع رسمی استفاده کنید."
        )
    except Exception:
        logger.exception("song identification failed")
        await message.reply_text("تشخیص آهنگ الان ممکن نبود. بعدا دوباره تلاش کنید.")
