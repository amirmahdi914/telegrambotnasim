"""پنل ادمین: سفارش‌ها، مشتریان و پروژه‌ها جدا و مرتب."""
import asyncio
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import owner_id
from database import (
    add_project,
    list_orders,
    list_projects,
    list_users,
    list_warning_stats,
    set_order_status,
)

P_TITLE, P_DETAILS, P_CLIENT, P_PHONE, P_TG = range(5)


def is_owner(update: Update) -> bool:
    oid = owner_id()
    user = update.effective_user
    return bool(oid and user and user.id == oid)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📥 سفارش‌های جدید", callback_data="adm:new")],
            [InlineKeyboardButton("📋 همه سفارش‌ها", callback_data="adm:all")],
            [InlineKeyboardButton("👤 مشتریان", callback_data="adm:users")],
            [InlineKeyboardButton("📁 پروژه‌ها", callback_data="adm:projects")],
            [InlineKeyboardButton("➕ ثبت پروژه جدید", callback_data="adm:addproj")],
            [InlineKeyboardButton("⚠️ اخطارهای گروه", callback_data="adm:warns")],
        ]
    )


def _format_order(row) -> str:
    return (
        f"#{row['id']} | {row['status']}\n"
        f"{row['category']} / {row['service']}\n"
        f"{row['description']}\n"
        f"تلفن: {row['phone']}\n"
        f"تلگرام: {row['telegram_handle']}\n"
        f"نام: {row['full_name']}\n"
        f"تاریخ: {row['created_at']}"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        await update.message.reply_text("این بخش فقط برای ادمین است.")
        return
    await update.message.reply_text("پنل ادمین:", reply_markup=admin_keyboard())


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_owner(update):
        await query.edit_message_text("دسترسی ندارید.")
        return ConversationHandler.END

    action = query.data.split(":", 1)[1]
    if action == "new":
        rows = list_orders(status="new")
        text = "سفارش جدیدی نیست." if not rows else "\n\n".join(_format_order(r) for r in rows)
        await query.edit_message_text("📥 سفارش‌های جدید\n\n" + text, reply_markup=admin_keyboard())
        return ConversationHandler.END
    if action == "all":
        rows = list_orders()
        text = "سفارشی نیست." if not rows else "\n\n".join(_format_order(r) for r in rows)
        await query.edit_message_text("📋 همه سفارش‌ها\n\n" + text, reply_markup=admin_keyboard())
        return ConversationHandler.END
    if action == "users":
        rows = list_users()
        if not rows:
            text = "مشتری ثبت نشده."
        else:
            lines = [
                f"{r['full_name']} | @{r['username'] or '-'} | {r['phone'] or '-'}"
                for r in rows
            ]
            text = "\n".join(lines)
        await query.edit_message_text("👤 مشتریان\n\n" + text, reply_markup=admin_keyboard())
        return ConversationHandler.END
    if action == "projects":
        rows = list_projects()
        if not rows:
            text = "پروژه‌ای ثبت نشده."
        else:
            parts = []
            for r in rows:
                parts.append(
                    f"#{r['id']} {r['title']}\n"
                    f"{r['details']}\n"
                    f"صاحب کار: {r['client_name'] or '-'}\n"
                    f"تلفن: {r['client_phone'] or '-'}\n"
                    f"تلگرام: {r['client_telegram'] or '-'}\n"
                    f"منبع: {r['source'] or '-'}"
                )
            text = "\n\n".join(parts)
        await query.edit_message_text("📁 پروژه‌ها\n\n" + text, reply_markup=admin_keyboard())
        return ConversationHandler.END
    if action == "warns":
        rows = list_warning_stats()
        if not rows:
            text = "اخطاری ثبت نشده."
        else:
            text = "\n".join(
                f"گروه {r['chat_id']} | کاربر {r['user_id']} | {r['count']} اخطار"
                for r in rows
            )
        await query.edit_message_text("⚠️ اخطارهای گروه\n\n" + text, reply_markup=admin_keyboard())
        return ConversationHandler.END
    if action == "addproj":
        await query.edit_message_text("عنوان پروژه را بفرستید. برای لغو /cancel")
        return P_TITLE
    return ConversationHandler.END


async def project_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update):
        return ConversationHandler.END
    context.user_data["p_title"] = (update.message.text or "").strip()
    await update.message.reply_text("جزئیات کامل پروژه را بنویسید.")
    return P_DETAILS


async def project_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["p_details"] = (update.message.text or "").strip()
    await update.message.reply_text("نام صاحب کار را بفرستید.")
    return P_CLIENT


async def project_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["p_client"] = (update.message.text or "").strip()
    await update.message.reply_text("شماره تماس صاحب کار را بفرستید.")
    return P_PHONE


async def project_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["p_phone"] = (update.message.text or "").strip()
    await update.message.reply_text("آیدی تلگرام صاحب کار را بفرستید.")
    return P_TG


async def project_tg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handle = (update.message.text or "").strip()
    pid = add_project(
        title=context.user_data.get("p_title", ""),
        details=context.user_data.get("p_details", ""),
        client_name=context.user_data.get("p_client", ""),
        client_phone=context.user_data.get("p_phone", ""),
        client_telegram=handle,
        source="ثبت دستی ادمین",
    )
    context.user_data.clear()
    await update.message.reply_text(
        f"پروژه #{pid} ذخیره شد.",
        reply_markup=admin_keyboard(),
    )
    return ConversationHandler.END


async def done_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        return
    if not context.args:
        await update.message.reply_text("مثال: /done 12")
        return
    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شماره سفارش باید عدد باشد.")
        return
    ok = set_order_status(order_id, "done")
    await update.message.reply_text("انجام شد." if ok else "سفارش پیدا نشد.")


async def cancel_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("لغو شد.", reply_markup=admin_keyboard())
    return ConversationHandler.END


def build_admin_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback, pattern=r"^adm:")],
        states={
            P_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_title)],
            P_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_details)],
            P_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_client)],
            P_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_phone)],
            P_TG: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_tg)],
        },
        fallbacks=[CommandHandler("cancel", cancel_project)],
        name="admin_project",
        per_chat=True,
        per_user=True,
    )
