import functools
import logging

from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

from db import get_connection, init_db
from event_calendar import Calendar, parse_date, parse_time
from secrets import API_TOKEN
from users import Users

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалогов: бот помнит, на каком шаге находится пользователь
(
    CREATE_NAME,
    CREATE_DATE,
    CREATE_TIME,
    CREATE_DETAILS,
    EDIT_NAME,
    EDIT_DATE,
    EDIT_TIME,
    EDIT_DETAILS,
    ASK_NAME,
) = range(9)

KEEP = "-"  # ввод «-» при редактировании оставляет старое значение
TEXT = Filters.text & ~Filters.command

HELP_TEXT = (
    "Команды:\n"
    "/register — зарегистрироваться\n"
    "/create_event — создать событие\n"
    "/events — все мои события\n"
    "/read_event [название] — показать событие\n"
    "/edit_event — изменить событие\n"
    "/delete_event [название] — удалить событие\n"
    "/cancel — отменить текущее действие"
)


def calendar(context) -> Calendar:
    return context.bot_data["calendar"]


def users(context) -> Users:
    return context.bot_data["users"]


def registered_only(handler):
    """Пускает к команде только зарегистрированных пользователей."""

    @functools.wraps(handler)
    def wrapper(update, context):
        if not users(context).is_registered(update.effective_user.id):
            update.message.reply_text("Сначала зарегистрируйтесь: /register")
            return ConversationHandler.END
        return handler(update, context)

    return wrapper


# ---------- Общие команды ----------

def start(update, context):
    update.message.reply_text("Привет! Я бот-календарь.\n\n" + HELP_TEXT)


def register(update, context):
    user = update.effective_user
    if users(context).register(user.id, user.username, user.first_name):
        update.message.reply_text(
            f"Готово, {user.first_name}! Теперь можно создать событие: /create_event"
        )
    else:
        update.message.reply_text("Вы уже зарегистрированы.")


@registered_only
def display_events(update, context):
    update.message.reply_text(calendar(context).display_events(update.effective_user.id))


def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


# ---------- Создание события: название → дата → время → описание ----------

@registered_only
def create_start(update, context):
    context.user_data.clear()
    update.message.reply_text("Как назовём событие?")
    return CREATE_NAME


def create_name(update, context):
    name = update.message.text.strip()
    if calendar(context).event_exists(update.effective_user.id, name):
        update.message.reply_text("Событие с таким названием уже есть. Введите другое:")
        return CREATE_NAME
    context.user_data["name"] = name
    update.message.reply_text("Дата события (ДД.ММ.ГГГГ):")
    return CREATE_DATE


def create_date(update, context):
    try:
        parse_date(update.message.text)
    except ValueError:
        update.message.reply_text("Неверная дата. Пример: 25.12.2026")
        return CREATE_DATE
    context.user_data["date"] = update.message.text.strip()
    update.message.reply_text("Время события (ЧЧ:ММ):")
    return CREATE_TIME


def create_time(update, context):
    try:
        parse_time(update.message.text)
    except ValueError:
        update.message.reply_text("Неверное время. Пример: 18:30")
        return CREATE_TIME
    context.user_data["time"] = update.message.text.strip()
    update.message.reply_text("Описание события (или /skip, чтобы пропустить):")
    return CREATE_DETAILS


def create_details(update, context):
    details = "" if update.message.text == "/skip" else update.message.text.strip()
    data = context.user_data
    result = calendar(context).create_event(
        update.effective_user.id, data["name"], data["date"], data["time"], details
    )
    data.clear()
    update.message.reply_text(result)
    return ConversationHandler.END


# ---------- Редактирование: название → дата → время → описание («-» = без изменений) ----------

@registered_only
def edit_start(update, context):
    context.user_data.clear()
    update.message.reply_text("Какое событие изменить? Введите название:")
    return EDIT_NAME


def edit_name(update, context):
    name = update.message.text.strip()
    if not calendar(context).event_exists(update.effective_user.id, name):
        update.message.reply_text("Такого события нет. Введите название ещё раз или /cancel:")
        return EDIT_NAME
    context.user_data["name"] = name
    update.message.reply_text(f"Новая дата (ДД.ММ.ГГГГ) или «{KEEP}», чтобы оставить:")
    return EDIT_DATE


def edit_date(update, context):
    text = update.message.text.strip()
    if text != KEEP:
        try:
            parse_date(text)
        except ValueError:
            update.message.reply_text("Неверная дата. Пример: 25.12.2026")
            return EDIT_DATE
        context.user_data["date"] = text
    update.message.reply_text(f"Новое время (ЧЧ:ММ) или «{KEEP}»:")
    return EDIT_TIME


def edit_time(update, context):
    text = update.message.text.strip()
    if text != KEEP:
        try:
            parse_time(text)
        except ValueError:
            update.message.reply_text("Неверное время. Пример: 18:30")
            return EDIT_TIME
        context.user_data["time"] = text
    update.message.reply_text(f"Новое описание или «{KEEP}»:")
    return EDIT_DETAILS


def edit_details(update, context):
    text = update.message.text.strip()
    data = context.user_data
    result = calendar(context).edit_event(
        update.effective_user.id,
        data["name"],
        new_date=data.get("date"),
        new_description=None if text == KEEP else text,
        new_time=data.get("time"),
    )
    data.clear()
    update.message.reply_text(result)
    return ConversationHandler.END


# ---------- Просмотр и удаление: название можно передать сразу или ввести следующим сообщением ----------

def run_action(update, context, action, name):
    user_id = update.effective_user.id
    if action == "read":
        update.message.reply_text(calendar(context).read_event(user_id, name))
    else:
        update.message.reply_text(calendar(context).delete_event(user_id, name))
    return ConversationHandler.END


def action_start(action):
    @registered_only
    def handler(update, context):
        name = " ".join(context.args).strip()
        if name:
            return run_action(update, context, action, name)
        context.user_data["action"] = action
        update.message.reply_text("Введите название события:")
        return ASK_NAME

    return handler


def ask_name(update, context):
    action = context.user_data.pop("action")
    return run_action(update, context, action, update.message.text.strip())


def error_handler(update, context):
    logger.exception("Ошибка при обработке обновления", exc_info=context.error)
    if update and update.effective_message:
        update.effective_message.reply_text("Что-то пошло не так. Попробуйте ещё раз.")


def create_updater(conn, token=API_TOKEN):
    """Собирает бота: подключает хранилища и регистрирует обработчики."""
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.bot_data["calendar"] = Calendar(conn)
    dispatcher.bot_data["users"] = Users(conn)

    cancel_handler = CommandHandler("cancel", cancel)

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("create_event", create_start)],
        states={
            CREATE_NAME: [MessageHandler(TEXT, create_name)],
            CREATE_DATE: [MessageHandler(TEXT, create_date)],
            CREATE_TIME: [MessageHandler(TEXT, create_time)],
            CREATE_DETAILS: [
                MessageHandler(TEXT, create_details),
                CommandHandler("skip", create_details),
            ],
        },
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("edit_event", edit_start)],
        states={
            EDIT_NAME: [MessageHandler(TEXT, edit_name)],
            EDIT_DATE: [MessageHandler(TEXT, edit_date)],
            EDIT_TIME: [MessageHandler(TEXT, edit_time)],
            EDIT_DETAILS: [MessageHandler(TEXT, edit_details)],
        },
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("read_event", action_start("read")),
            CommandHandler("delete_event", action_start("delete")),
        ],
        states={ASK_NAME: [MessageHandler(TEXT, ask_name)]},
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))

    dispatcher.add_handler(CommandHandler(["start", "help"], start))
    dispatcher.add_handler(CommandHandler("register", register))
    dispatcher.add_handler(CommandHandler("events", display_events))
    dispatcher.add_handler(cancel_handler)
    dispatcher.add_handler(MessageHandler(Filters.all, unknown))
    dispatcher.add_error_handler(error_handler)
    return updater


def main():
    conn = get_connection()
    init_db(conn)
    updater = create_updater(conn)
    updater.start_polling()
    logger.info("Бот запущен")
    updater.idle()
    conn.close()


if __name__ == "__main__":
    main()
