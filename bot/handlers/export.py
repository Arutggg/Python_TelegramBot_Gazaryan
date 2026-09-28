"""Выгрузка событий: бот запрашивает файл у веб-приложения и присылает его пользователю."""
import io
import logging
import urllib.request

from django.conf import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from calendar_app.tokens import make_token

from ..utils import registered_callback, registered_only

logger = logging.getLogger(__name__)


def export_url(user, file_format, base_url=None):
    return f"{base_url or settings.WEB_URL}/export/{make_token(user)}/?format={file_format}"


def download_export(url):
    """Запрашивает выгрузку у веб-приложения и возвращает содержимое файла."""
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read()


@registered_only
def export(update, context, calendar):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📄 CSV", callback_data="export:csv"),
        InlineKeyboardButton("🧾 JSON", callback_data="export:json"),
    ]])
    update.message.reply_text(
        "В каком формате выгрузить события?\n\n"
        f"Или скачайте в браузере:\n{export_url(calendar.user, 'csv')}",
        reply_markup=keyboard,
    )


@registered_callback
def send_export(update, context, calendar):
    """Нажатие на кнопку формата."""
    query = update.callback_query
    file_format = query.data.split(":")[1]
    try:
        content = download_export(export_url(calendar.user, file_format, settings.INTERNAL_WEB_URL))
    except OSError:
        logger.exception("Не удалось получить выгрузку")
        query.answer("Веб-приложение недоступно, попробуйте позже.", show_alert=True)
        return
    query.answer()
    context.bot.send_document(
        chat_id=calendar.user.telegram_id,
        document=io.BytesIO(content),
        filename=f"events.{file_format}",
        caption="Ваши события",
    )


def handlers():
    return [
        CommandHandler("export", export),
        CallbackQueryHandler(send_export, pattern=r"^export:(csv|json)$"),
    ]
