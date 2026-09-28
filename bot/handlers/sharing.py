"""Публичные события: поделиться, скрыть, посмотреть чужие."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from calendar_app.meetings import find_user
from calendar_app.services import CalendarError, public_events

from ..formatting import format_events
from ..utils import command_text, registered_callback, registered_only


def share_keyboard(events):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'🌐' if event.is_public else '🔒'} {event.name}",
            callback_data=f"share:{event.id}",
        )]
        for event in events
    ])


def set_visibility(update, calendar, name, is_public):
    try:
        calendar.set_public(name, is_public)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return
    update.message.reply_text(
        f"Событие «{name}» теперь видят другие пользователи." if is_public else f"Событие «{name}» скрыто."
    )


@registered_only
def share(update, context, calendar):
    name = command_text(context)
    if name:
        set_visibility(update, calendar, name, True)
        return
    events = calendar.display_events()
    if not events:
        update.message.reply_text("Событий пока нет.")
        return
    update.message.reply_text(
        "Нажмите на событие, чтобы открыть или скрыть его.\n🌐 — видят все, 🔒 — только вы.",
        reply_markup=share_keyboard(events),
    )


@registered_only
def unshare(update, context, calendar):
    name = command_text(context)
    if not name:
        update.message.reply_text("Формат: /unshare название")
        return
    set_visibility(update, calendar, name, False)


@registered_callback
def toggle_share(update, context, calendar):
    """Нажатие на событие в списке /share."""
    query = update.callback_query
    try:
        event = calendar.toggle_public(int(query.data.split(":")[1]))
    except CalendarError as error:
        query.answer(str(error), show_alert=True)
        return
    query.answer("Теперь видят все" if event.is_public else "Скрыто")
    query.edit_message_reply_markup(reply_markup=share_keyboard(calendar.display_events()))


@registered_only
def shared(update, context, calendar):
    identifier = command_text(context)
    if not identifier:
        events = public_events(exclude_user=calendar.user)
        update.message.reply_text(
            "Общие события других пользователей:\n\n"
            + format_events(events, "Общих событий нет.", with_owner=True)
        )
        return
    owner = find_user(identifier)
    if owner is None:
        update.message.reply_text("Такой пользователь не зарегистрирован в боте.")
        return
    update.message.reply_text(
        f"Общие события {owner}:\n\n" + format_events(public_events(owner=owner), "Общих событий нет.")
    )


def handlers():
    return [
        CommandHandler("share", share),
        CommandHandler("unshare", unshare),
        CommandHandler("shared", shared),
        CallbackQueryHandler(toggle_share, pattern=r"^share:\d+$"),
    ]
