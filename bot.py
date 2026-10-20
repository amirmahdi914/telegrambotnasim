"""بات تلگرام کسب‌وکار: پنل مشتری، پنل ادمین، دیتابیس و مدیریت گروه."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from admin_panel import admin_command, build_admin_conversation, done_order
from config import (
    DAILY_PRICE_REPORT_HOUR,
    JOB_CHECK_INTERVAL_HOURS,
    TELEGRAM_BOT_TOKEN,
    owner_id,
)
from customer import build_customer_conversation
from database import add_project, init_db
from group_mod import moderate_group
from job_scraper import fetch_new_jobs, format_jobs_message
from music_id import identify_audio
from price_fetcher import format_price_report
from responses import DEFAULT_RESPONSE, FIXED_RESPONSES

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("در حال دریافت قیمت‌ها...")
    report = format_price_report()
    await update.message.reply_text(report)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "دستورها:\n"
        "/start شروع پنل خدمات\n"
        "/price قیمت دلار و طلا\n"
        "/cancel لغو فرم\n"
        "/admin پنل ادمین (فقط صاحب بات)\n"
        "/done شماره‌سفارش  علامت‌زدن انجام‌شده\n\n"
        "ویس یا فایل آهنگ بفرستید تا نام آهنگ تشخیص داده شود."
    )


async def handle_private_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip().lower()
    lowered = text.replace(" ", "")
    if any(site in lowered for site in ("youtube.com", "youtu.be", "instagram.com", "instagr.am")):
        await update.message.reply_text(
            "دانلود فیلم از یوتیوب و اینستاگرام فعال نیست، چون معمولا حق نشر دارد."
        )
        return
    for keyword, response in FIXED_RESPONSES.items():
        if keyword in text:
            await update.message.reply_text(response)
            return
    await update.message.reply_text(DEFAULT_RESPONSE)


async def daily_price_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    oid = owner_id()
    if not oid:
        logger.warning("OWNER_CHAT_ID تنظیم نشده.")
        return
    await context.bot.send_message(chat_id=oid, text=format_price_report())


async def job_check_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    oid = owner_id()
    if not oid:
        return
    new_jobs = fetch_new_jobs()
    if not new_jobs:
        logger.info("پروژه جدیدی پیدا نشد.")
        return
    for job in new_jobs:
        add_project(
            title=job["title"],
            details=f"لینک آگهی: {job['link']}",
            source=job.get("link", "job site"),
        )
    await context.bot.send_message(chat_id=oid, text=format_jobs_message(new_jobs))


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN را در فایل .env بگذارید.")

    init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["owner_id"] = owner_id()

    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("done", done_order))
    app.add_handler(build_admin_conversation())
    app.add_handler(build_customer_conversation())
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            moderate_group,
        )
    )
    app.add_handler(
        MessageHandler(filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE, identify_audio)
    )
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            handle_private_text,
        )
    )

    job_queue = app.job_queue
    job_queue.run_repeating(
        job_check_task, interval=JOB_CHECK_INTERVAL_HOURS * 3600, first=20
    )
    job_queue.run_daily(
        daily_price_job,
        time=__import__("datetime").time(hour=DAILY_PRICE_REPORT_HOUR, minute=0),
    )

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
