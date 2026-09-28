import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from db import get_connection, init_db
from event_calendar import Calendar
from secrets import API_TOKEN

HELP_TEXT = (
    "Команды:\n"
    "/create_event название | ДД.ММ.ГГГГ | ЧЧ:ММ | описание — создать событие\n"
    "/read_event название — показать событие\n"
    "/edit_event название | ДД.ММ.ГГГГ | описание — изменить событие\n"
    "/delete_event название — удалить событие\n"
    "/events — все события"
)

conn = get_connection()
init_db(conn)
calendar = Calendar(conn)


def split_parts(context):
    """Делит аргументы команды по «|» на список частей."""
    return [part.strip() for part in " ".join(context.args).split("|")]


def start(update, context):
    update.message.reply_text("Привет! Я бот-календарь.\n\n" + HELP_TEXT)


def create_event(update, context):
    parts = split_parts(context)
    if len(parts) < 3 or not parts[0]:
        update.message.reply_text(
            "Формат: /create_event название | ДД.ММ.ГГГГ | ЧЧ:ММ | описание"
        )
        return
    details = parts[3] if len(parts) > 3 else ""
    update.message.reply_text(calendar.create_event(parts[0], parts[1], parts[2], details))


def read_event(update, context):
    name = " ".join(context.args).strip()
    if not name:
        update.message.reply_text("Формат: /read_event название")
        return
    update.message.reply_text(calendar.read_event(name))


def edit_event(update, context):
    parts = split_parts(context)
    if len(parts) < 2 or not parts[0]:
        update.message.reply_text("Формат: /edit_event название | ДД.ММ.ГГГГ | описание")
        return
    new_date = parts[1] or None
    new_description = parts[2] if len(parts) > 2 else None
    update.message.reply_text(calendar.edit_event(parts[0], new_date, new_description))


def delete_event(update, context):
    name = " ".join(context.args).strip()
    if not name:
        update.message.reply_text("Формат: /delete_event название")
        return
    update.message.reply_text(calendar.delete_event(name))


def display_events(update, context):
    update.message.reply_text(calendar.display_events())


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


def main():
    updater = Updater(token=API_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler(["start", "help"], start))
    dispatcher.add_handler(CommandHandler("create_event", create_event))
    dispatcher.add_handler(CommandHandler("read_event", read_event))
    dispatcher.add_handler(CommandHandler("edit_event", edit_event))
    dispatcher.add_handler(CommandHandler("delete_event", delete_event))
    dispatcher.add_handler(CommandHandler("events", display_events))
    dispatcher.add_handler(MessageHandler(Filters.text | Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
