import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import notes
from secrets import API_TOKEN

HELP_TEXT = (
    "Команды для заметок:\n"
    "/add название | текст — создать заметку\n"
    "/read название — прочитать заметку\n"
    "/edit название | новый текст — изменить заметку\n"
    "/delete название — удалить заметку\n"
    "/list — заметки от короткой к длинной\n"
    "/sorted — заметки от длинной к короткой"
)


def split_args(context):
    """Делит аргументы команды «название | текст» на две части."""
    name, _, text = " ".join(context.args).partition("|")
    return name.strip(), text.strip()


def start(update, context):
    update.message.reply_text("Привет! Я бот для заметок.\n\n" + HELP_TEXT)


def add_note(update, context):
    name, text = split_args(context)
    if not name or not text:
        update.message.reply_text("Формат: /add название | текст")
        return
    update.message.reply_text(notes.create_note(name, text))


def read_note(update, context):
    name, _ = split_args(context)
    if not name:
        update.message.reply_text("Формат: /read название")
        return
    update.message.reply_text(notes.read_note(name))


def edit_note(update, context):
    name, text = split_args(context)
    if not name or not text:
        update.message.reply_text("Формат: /edit название | новый текст")
        return
    update.message.reply_text(notes.edit_note(name, text))


def delete_note(update, context):
    name, _ = split_args(context)
    if not name:
        update.message.reply_text("Формат: /delete название")
        return
    update.message.reply_text(notes.delete_note(name))


def list_notes(update, context):
    update.message.reply_text(notes.display_notes())


def sorted_notes(update, context):
    update.message.reply_text(notes.display_sorted_notes())


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


def main():
    updater = Updater(token=API_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler(["start", "help"], start))
    dispatcher.add_handler(CommandHandler("add", add_note))
    dispatcher.add_handler(CommandHandler("read", read_note))
    dispatcher.add_handler(CommandHandler("edit", edit_note))
    dispatcher.add_handler(CommandHandler("delete", delete_note))
    dispatcher.add_handler(CommandHandler("list", list_notes))
    dispatcher.add_handler(CommandHandler("sorted", sorted_notes))
    dispatcher.add_handler(MessageHandler(Filters.text | Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
