"""Сборка бота: регистрирует обработчики из модулей bot.handlers."""
import logging

from django.conf import settings
from django.db import close_old_connections, connection
from telegram import Update
from telegram.ext import CommandHandler, Filters, MessageHandler, TypeHandler, Updater

from .handlers import common, events, export, meetings, sharing
from .utils import cancel

logger = logging.getLogger(__name__)


def refresh_db_connection(update, context):
    """Бот работает долго: перед каждым апдейтом закрываем устаревшие соединения с БД."""
    if not connection.in_atomic_block:  # внутри транзакции (например, в тестах) не трогаем
        close_old_connections()


def error_handler(update, context):
    logger.exception("Ошибка при обработке обновления", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text("Что-то пошло не так. Попробуйте ещё раз.")


def create_updater(token=None):
    updater = Updater(token=token or settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(TypeHandler(Update, refresh_db_connection), group=-1)

    # Диалоги регистрируются первыми: пока диалог идёт, текст пользователя — ответ на его шаг
    for module in (events, meetings, sharing, export, common):
        for handler in module.handlers():
            dispatcher.add_handler(handler)

    dispatcher.add_handler(CommandHandler("cancel", cancel))
    dispatcher.add_handler(MessageHandler(Filters.all, common.unknown))
    dispatcher.add_error_handler(error_handler)
    return updater
