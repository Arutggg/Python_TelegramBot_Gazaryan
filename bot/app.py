import functools
import logging

from django.conf import settings
from django.db import close_old_connections, connection
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    TypeHandler,
    Updater,
)

from calendar_app.services import (
    DATE_FORMAT,
    TIME_FORMAT,
    Calendar,
    CalendarError,
    get_user,
    parse_date,
    parse_time,
    register_user,
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


def format_event(event):
    text = f"📌 {event.name} — {event.date.strftime(DATE_FORMAT)} в {event.time.strftime(TIME_FORMAT)}"
    if event.details:
        text += f"\n{event.details}"
    return text


def format_events(events, empty_text="Событий пока нет."):
    if not events:
        return empty_text
    return "\n\n".join(format_event(event) for event in events)


def registered_only(handler):
    """Пускает к команде только зарегистрированных и передаёт в обработчик его календарь."""

    @functools.wraps(handler)
    def wrapper(update, context):
        user = get_user(update.effective_user.id)
        if user is None:
            update.message.reply_text("Сначала зарегистрируйтесь: /register")
            return ConversationHandler.END
        return handler(update, context, Calendar(user))

    return wrapper


# ---------- Общие команды ----------

def start(update, context):
    update.message.reply_text("Привет! Я бот-календарь.\n\n" + HELP_TEXT)


def register(update, context):
    tg_user = update.effective_user
    _, created = register_user(tg_user.id, tg_user.username, tg_user.first_name)
    if created:
        update.message.reply_text(
            f"Готово, {tg_user.first_name}! Теперь можно создать событие: /create_event"
        )
    else:
        update.message.reply_text("Вы уже зарегистрированы.")


@registered_only
def display_events(update, context, calendar):
    update.message.reply_text(format_events(calendar.display_events()))


def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


# ---------- Создание события: название → дата → время → описание ----------

@registered_only
def create_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Как назовём событие?")
    return CREATE_NAME


@registered_only
def create_name(update, context, calendar):
    name = update.message.text.strip()
    if calendar.event_exists(name):
        update.message.reply_text("Событие с таким названием уже есть. Введите другое:")
        return CREATE_NAME
    context.user_data["name"] = name
    update.message.reply_text("Дата события (ДД.ММ.ГГГГ):")
    return CREATE_DATE


def create_date(update, context):
    try:
        parse_date(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return CREATE_DATE
    context.user_data["date"] = update.message.text.strip()
    update.message.reply_text("Время события (ЧЧ:ММ):")
    return CREATE_TIME


def create_time(update, context):
    try:
        parse_time(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return CREATE_TIME
    context.user_data["time"] = update.message.text.strip()
    update.message.reply_text("Описание события (или /skip, чтобы пропустить):")
    return CREATE_DETAILS


@registered_only
def create_details(update, context, calendar):
    details = "" if update.message.text == "/skip" else update.message.text.strip()
    data = context.user_data
    try:
        calendar.create_event(data["name"], data["date"], data["time"], details)
        update.message.reply_text(f"Событие «{data['name']}» создано.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    data.clear()
    return ConversationHandler.END


# ---------- Редактирование: название → дата → время → описание («-» = без изменений) ----------

@registered_only
def edit_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Какое событие изменить? Введите название:")
    return EDIT_NAME


@registered_only
def edit_name(update, context, calendar):
    name = update.message.text.strip()
    if not calendar.event_exists(name):
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
        except CalendarError as error:
            update.message.reply_text(str(error))
            return EDIT_DATE
        context.user_data["date"] = text
    update.message.reply_text(f"Новое время (ЧЧ:ММ) или «{KEEP}»:")
    return EDIT_TIME


def edit_time(update, context):
    text = update.message.text.strip()
    if text != KEEP:
        try:
            parse_time(text)
        except CalendarError as error:
            update.message.reply_text(str(error))
            return EDIT_TIME
        context.user_data["time"] = text
    update.message.reply_text(f"Новое описание или «{KEEP}»:")
    return EDIT_DETAILS


@registered_only
def edit_details(update, context, calendar):
    text = update.message.text.strip()
    data = context.user_data
    try:
        calendar.edit_event(
            data["name"],
            new_date=data.get("date"),
            new_description=None if text == KEEP else text,
            new_time=data.get("time"),
        )
        update.message.reply_text(f"Событие «{data['name']}» обновлено.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    data.clear()
    return ConversationHandler.END


# ---------- Просмотр и удаление: название можно передать сразу или ввести следующим сообщением ----------

def run_action(update, calendar, action, name):
    try:
        if action == "read":
            update.message.reply_text(format_event(calendar.read_event(name)))
        else:
            calendar.delete_event(name)
            update.message.reply_text(f"Событие «{name}» удалено.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    return ConversationHandler.END


def action_start(action):
    @registered_only
    def handler(update, context, calendar):
        name = " ".join(context.args).strip()
        if name:
            return run_action(update, calendar, action, name)
        context.user_data["action"] = action
        update.message.reply_text("Введите название события:")
        return ASK_NAME

    return handler


@registered_only
def ask_name(update, context, calendar):
    action = context.user_data.pop("action")
    return run_action(update, calendar, action, update.message.text.strip())


def error_handler(update, context):
    logger.exception("Ошибка при обработке обновления", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text("Что-то пошло не так. Попробуйте ещё раз.")


def refresh_db_connection(update, context):
    """Бот работает долго: перед каждым апдейтом закрываем устаревшие соединения с БД."""
    if not connection.in_atomic_block:  # внутри транзакции (например, в тестах) не трогаем
        close_old_connections()


def create_updater(token=None):
    """Собирает бота и регистрирует обработчики."""
    updater = Updater(token=token or settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(TypeHandler(Update, refresh_db_connection), group=-1)

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
