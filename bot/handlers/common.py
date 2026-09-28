"""Общие команды: справка, регистрация, вход и календарь целиком."""
from django.conf import settings
from telegram.ext import CommandHandler

from calendar_app.meetings import user_meetings
from calendar_app.services import public_events, register_user
from calendar_app.tokens import make_token

from ..formatting import format_events, format_meetings
from ..utils import registered_only

HELP_TEXT = (
    "Команды:\n"
    "/register — зарегистрироваться\n"
    "/login — подключить Telegram ID к учётной записи и получить ссылку на личный кабинет\n"
    "/calendar — мой календарь: события, встречи и общие события\n"
    "/create_event — создать событие\n"
    "/events — все мои события\n"
    "/read_event [название] — показать событие\n"
    "/edit_event — изменить событие\n"
    "/delete_event [название] — удалить событие\n"
    "/share [название] — поделиться событием (без названия — выбрать кнопками)\n"
    "/unshare название — скрыть событие\n"
    "/shared [@username] — общие события других пользователей\n"
    "/export — выгрузить мои события в CSV или JSON\n"
    "/meeting — назначить встречу другим пользователям\n"
    "/meetings — мои встречи и их статусы\n"
    "/cancel — отменить текущее действие"
)


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


def cabinet_url(user):
    return f"{settings.WEB_URL}/cabinet/{make_token(user)}/"


def login(update, context):
    """Подключает Telegram ID к учётной записи (создаёт её при необходимости)
    и присылает ссылку на личный кабинет. ID берём из самого сообщения, а не из
    текста команды: так нельзя войти под чужим ID."""
    tg_user = update.effective_user
    user, created = register_user(tg_user.id, tg_user.username, tg_user.first_name)
    update.message.reply_text(
        f"{'Учётная запись создана' if created else 'Вы вошли'}.\n"
        f"Ваш Telegram ID: {user.telegram_id}\n\n"
        f"Личный кабинет (ссылка действует неделю):\n{cabinet_url(user)}"
    )


@registered_only
def show_calendar(update, context, calendar):
    shared = public_events(exclude_user=calendar.user)
    update.message.reply_text(
        "🗓 Ваш календарь\n\n"
        "События:\n\n" + format_events(calendar.display_events())
        + "\n\nВстречи:\n\n" + format_meetings(user_meetings(calendar.user))
        + "\n\nОбщие события:\n\n"
        + format_events(shared, "Другие пользователи пока ничем не поделились.", with_owner=True)
    )


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


def handlers():
    return [
        CommandHandler(["start", "help"], start),
        CommandHandler("register", register),
        CommandHandler("login", login),
        CommandHandler("calendar", show_calendar),
    ]
