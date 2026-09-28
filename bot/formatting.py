"""Текстовое представление событий и встреч в сообщениях бота."""
from calendar_app.models import MeetingStatus
from calendar_app.services import DATE_FORMAT, TIME_FORMAT

STATUS_ICONS = {
    MeetingStatus.PENDING: "⏳",
    MeetingStatus.CONFIRMED: "✅",
    MeetingStatus.CANCELLED: "❌",
}


def format_when(obj):
    return f"{obj.date.strftime(DATE_FORMAT)} в {obj.time.strftime(TIME_FORMAT)}"


def format_event(event, with_owner=False):
    icon = "🌐" if event.is_public else "📌"
    owner = f" ({event.owner})" if with_owner else ""
    text = f"{icon} {event.name}{owner} — {format_when(event)}"
    if event.details:
        text += f"\n{event.details}"
    return text


def format_meeting(meeting):
    participants = ", ".join(
        f"{invitation.user} {STATUS_ICONS[invitation.status]}"
        for invitation in meeting.invitations.all()
    )
    return (
        f"{STATUS_ICONS[meeting.status]} {meeting.title} — {format_when(meeting)} "
        f"({meeting.duration_minutes} мин)\n"
        f"Статус: {meeting.get_status_display()}\n"
        f"Организатор: {meeting.organizer}\n"
        f"Участники: {participants}"
    )


def format_list(items, formatter, empty_text):
    """Список объектов через пустую строку или empty_text, если список пуст."""
    return "\n\n".join(formatter(item) for item in items) if items else empty_text


def format_events(events, empty_text="Событий пока нет.", with_owner=False):
    return format_list(events, lambda event: format_event(event, with_owner), empty_text)


def format_meetings(meetings, empty_text="Встреч пока нет."):
    return format_list(meetings, format_meeting, empty_text)
