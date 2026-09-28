"""Создание, просмотр, редактирование и удаление событий."""
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler

from calendar_app.services import CalendarError, parse_date, parse_time

from ..formatting import format_event, format_events
from ..states import (
    ASK_NAME,
    CREATE_DATE,
    CREATE_DETAILS,
    CREATE_NAME,
    CREATE_TIME,
    EDIT_DATE,
    EDIT_DETAILS,
    EDIT_NAME,
    EDIT_TIME,
    KEEP,
    SKIP,
)
from ..utils import TEXT, command_text, conversation, input_step, registered_only


@registered_only
def display_events(update, context, calendar):
    update.message.reply_text(format_events(calendar.display_events()))


# ---------- Создание: название → дата → время → описание ----------

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


create_date = input_step("date", parse_date, CREATE_DATE, CREATE_TIME, "Время события (ЧЧ:ММ):")
create_time = input_step(
    "time", parse_time, CREATE_TIME, CREATE_DETAILS,
    f"Описание события (или {SKIP}, чтобы пропустить):",
)


@registered_only
def create_details(update, context, calendar):
    text = update.message.text.strip()
    data = context.user_data
    try:
        calendar.create_event(data["name"], data["date"], data["time"], "" if text == SKIP else text)
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


edit_date = input_step("date", parse_date, EDIT_DATE, EDIT_TIME, f"Новое время (ЧЧ:ММ) или «{KEEP}»:", skip=KEEP)
edit_time = input_step("time", parse_time, EDIT_TIME, EDIT_DETAILS, f"Новое описание или «{KEEP}»:", skip=KEEP)


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


# ---------- Просмотр и удаление: название сразу после команды или следующим сообщением ----------

def read_event(update, calendar, name):
    update.message.reply_text(format_event(calendar.read_event(name)))


def delete_event(update, calendar, name):
    calendar.delete_event(name)
    update.message.reply_text(f"Событие «{name}» удалено.")


ACTIONS = {"read": read_event, "delete": delete_event}


def run_action(update, calendar, action, name):
    try:
        ACTIONS[action](update, calendar, name)
    except CalendarError as error:
        update.message.reply_text(str(error))
    return ConversationHandler.END


def action_start(action):
    @registered_only
    def handler(update, context, calendar):
        name = command_text(context)
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


def handlers():
    return [
        conversation(
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
        ),
        conversation(
            entry_points=[CommandHandler("edit_event", edit_start)],
            states={
                EDIT_NAME: [MessageHandler(TEXT, edit_name)],
                EDIT_DATE: [MessageHandler(TEXT, edit_date)],
                EDIT_TIME: [MessageHandler(TEXT, edit_time)],
                EDIT_DETAILS: [MessageHandler(TEXT, edit_details)],
            },
        ),
        conversation(
            entry_points=[
                CommandHandler("read_event", action_start("read")),
                CommandHandler("delete_event", action_start("delete")),
            ],
            states={ASK_NAME: [MessageHandler(TEXT, ask_name)]},
        ),
        CommandHandler("events", display_events),
    ]
