"""Встречи: назначение, приглашения и ответы на них."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler

from calendar_app.meetings import (
    DEFAULT_DURATION,
    create_meeting,
    parse_duration,
    respond_to_meeting,
    user_meetings,
)
from calendar_app.services import CalendarError, parse_date, parse_time

from ..formatting import format_meeting, format_meetings
from ..states import (
    MEETING_DATE,
    MEETING_DURATION,
    MEETING_PARTICIPANTS,
    MEETING_TIME,
    MEETING_TITLE,
    SKIP,
)
from ..utils import TEXT, conversation, input_step, registered_callback, registered_only


@registered_only
def meeting_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Тема встречи?")
    return MEETING_TITLE


meeting_title = input_step("title", str, MEETING_TITLE, MEETING_DATE, "Дата встречи (ДД.ММ.ГГГГ):")
meeting_date = input_step("date", parse_date, MEETING_DATE, MEETING_TIME, "Время начала (ЧЧ:ММ):")
meeting_time = input_step(
    "time", parse_time, MEETING_TIME, MEETING_DURATION,
    f"Длительность в минутах (или {SKIP} — {DEFAULT_DURATION} минут):",
)
meeting_duration = input_step(
    "duration", parse_duration, MEETING_DURATION, MEETING_PARTICIPANTS,
    "Кого пригласить? Напишите @username или Telegram ID через пробел.\n"
    "Участники должны быть зарегистрированы в боте.",
    skip=SKIP,
)


def invitation_keyboard(meeting):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Принять", callback_data=f"meeting:accept:{meeting.id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"meeting:decline:{meeting.id}"),
    ]])


def send_invitations(bot, organizer, meeting, invited):
    for user in invited:
        bot.send_message(
            chat_id=user.telegram_id,
            text=f"{organizer} приглашает вас на встречу:\n\n{format_meeting(meeting)}",
            reply_markup=invitation_keyboard(meeting),
        )


@registered_only
def meeting_participants(update, context, calendar):
    data = context.user_data
    identifiers = update.message.text.replace(",", " ").split()
    try:
        meeting, invited, problems = create_meeting(
            calendar.user, data["title"], data["date"], data["time"],
            data.get("duration", DEFAULT_DURATION), identifiers,
        )
    except CalendarError as error:
        update.message.reply_text(f"{error}\n\nВведите других участников или /cancel:")
        return MEETING_PARTICIPANTS
    data.clear()

    send_invitations(context.bot, calendar.user, meeting, invited)
    text = "Встреча создана, приглашения отправлены:\n\n" + format_meeting(meeting)
    if problems:
        text += "\n\nНе приглашены:\n" + "\n".join(problems)
    update.message.reply_text(text)
    return ConversationHandler.END


@registered_only
def list_meetings(update, context, calendar):
    meetings = user_meetings(calendar.user)
    if not meetings:
        update.message.reply_text("Встреч пока нет. Назначить: /meeting")
        return
    update.message.reply_text("Ваши встречи:\n\n" + format_meetings(meetings))


@registered_callback
def answer_invitation(update, context, calendar):
    """Нажатие «Принять» / «Отклонить» под приглашением."""
    query = update.callback_query
    _, action, meeting_id = query.data.split(":")
    accepted = action == "accept"
    try:
        meeting = respond_to_meeting(int(meeting_id), calendar.user, accept=accepted)
    except CalendarError as error:
        query.answer(str(error), show_alert=True)
        return
    query.answer()
    query.edit_message_text(
        f"Вы {'приняли' if accepted else 'отклонили'} приглашение.\n\n{format_meeting(meeting)}"
    )
    context.bot.send_message(
        chat_id=meeting.organizer.telegram_id,
        text=f"{calendar.user} {'принял(а)' if accepted else 'отклонил(а)'} приглашение.\n\n"
        f"{format_meeting(meeting)}",
    )


def handlers():
    return [
        conversation(
            entry_points=[CommandHandler("meeting", meeting_start)],
            states={
                MEETING_TITLE: [MessageHandler(TEXT, meeting_title)],
                MEETING_DATE: [MessageHandler(TEXT, meeting_date)],
                MEETING_TIME: [MessageHandler(TEXT, meeting_time)],
                MEETING_DURATION: [
                    MessageHandler(TEXT, meeting_duration),
                    CommandHandler("skip", meeting_duration),
                ],
                MEETING_PARTICIPANTS: [MessageHandler(TEXT, meeting_participants)],
            },
        ),
        CommandHandler("meetings", list_meetings),
        CallbackQueryHandler(answer_invitation, pattern=r"^meeting:(accept|decline):\d+$"),
    ]
