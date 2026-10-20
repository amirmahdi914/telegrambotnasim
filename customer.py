"""پنل مشتری: انتخاب خدمت، شرح مشکل، شماره و آیدی تلگرام."""
from __future__ import annotations

import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from catalog import CATEGORIES, CONTACT_PHONE
from database import add_order

SELECT_CATEGORY, SELECT_SERVICE, GET_DESC, GET_PHONE, GET_TELEGRAM = range(5)

PHONE_RE = re.compile(r"^09\d{9}$")
TG_RE = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key, cat in CATEGORIES.items():
        rows.append(
            [
                InlineKeyboardButton(
                    f"{cat['emoji']} {cat['title']}", callback_data=f"cat:{key}"
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def services_keyboard(category_key: str) -> InlineKeyboardMarkup:
    cat = CATEGORIES[category_key]
    rows = []
    for i, name in enumerate(cat["services"]):
        rows.append(
            [InlineKeyboardButton(name, callback_data=f"svc:{category_key}:{i}")]
        )
    rows.append([InlineKeyboardButton("بازگشت", callback_data="back:menu")])
    return InlineKeyboardMarkup(rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "سلام! به پنل خدمات خوش آمدید.\n"
        "یکی از بخش‌ها را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )
    return SELECT_CATEGORY


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "یکی از بخش‌ها را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )
    return SELECT_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    if key not in CATEGORIES:
        await query.edit_message_text("بخش نامعتبر است.")
        return ConversationHandler.END
    context.user_data["category"] = key
    cat = CATEGORIES[key]
    await query.edit_message_text(
        f"خدمات {cat['title']}:\nیکی را انتخاب کنید.",
        reply_markup=services_keyboard(key),
    )
    return SELECT_SERVICE


async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, key, idx = query.data.split(":")
    services = CATEGORIES[key]["services"]
    service = services[int(idx)]
    context.user_data["category"] = key
    context.user_data["service"] = service
    await query.edit_message_text(
        f"خدمت انتخابی: {service}\n\nلطفا مشکل خود را شرح دهید."
    )
    return GET_DESC


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("توضیحات خالی است. لطفا مشکل خود را شرح دهید.")
        return GET_DESC
    context.user_data["description"] = text
    await update.message.reply_text("شماره تلفن خود را وارد کنید (مثال: 09121234567)")
    return GET_PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = (update.message.text or "").strip().replace(" ", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    if phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    if not PHONE_RE.match(phone):
        await update.message.reply_text(
            "شماره معتبر نیست. یک شماره موبایل ایران مثل 09121234567 بفرستید."
        )
        return GET_PHONE
    context.user_data["phone"] = phone
    await update.message.reply_text("آیدی تلگرام خود را وارد کنید (مثال: @username)")
    return GET_TELEGRAM


async def get_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handle = (update.message.text or "").strip()
    if not handle or not TG_RE.match(handle):
        await update.message.reply_text(
            "آیدی تلگرام خالی یا نامعتبر است. مثل @username بفرستید."
        )
        return GET_TELEGRAM
    if not handle.startswith("@"):
        handle = "@" + handle
    context.user_data["telegram_handle"] = handle

    user = update.effective_user
    category_key = context.user_data["category"]
    category_title = CATEGORIES[category_key]["title"]
    service = context.user_data["service"]
    description = context.user_data["description"]
    phone = context.user_data["phone"]

    order_id = add_order(
        telegram_id=user.id,
        username=user.username,
        full_name=user.full_name or "",
        category=category_title,
        service=service,
        description=description,
        phone=phone,
        telegram_handle=handle,
    )

    owner_id = context.application.bot_data.get("owner_id")
    if owner_id:
        await context.bot.send_message(
            chat_id=owner_id,
            text=(
                "📥 سفارش جدید\n"
                f"شماره سفارش: {order_id}\n"
                f"بخش: {category_title}\n"
                f"خدمت: {service}\n"
                f"توضیحات: {description}\n"
                f"تلفن مشتری: {phone}\n"
                f"آیدی تلگرام: {handle}\n"
                f"نام: {user.full_name}\n"
                f"یوزرنیم: @{user.username or '-'}"
            ),
        )

    await update.message.reply_text(
        "درخواست شما ثبت شد و برای ادمین ارسال گردید.\n"
        f"پیام بدهید: {CONTACT_PHONE}\n\n"
        "برای سفارش جدید /start را بزنید."
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("لغو شد. برای شروع دوباره /start را بزنید.")
    return ConversationHandler.END


def build_customer_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE)
        ],
        states={
            SELECT_CATEGORY: [
                CallbackQueryHandler(category_chosen, pattern=r"^cat:"),
                CallbackQueryHandler(show_menu, pattern=r"^back:menu$"),
            ],
            SELECT_SERVICE: [
                CallbackQueryHandler(service_chosen, pattern=r"^svc:"),
                CallbackQueryHandler(show_menu, pattern=r"^back:menu$"),
            ],
            GET_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            GET_TELEGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_telegram)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="customer_flow",
        persistent=False,
        per_chat=True,
        per_user=True,
    )
