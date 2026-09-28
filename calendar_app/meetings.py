"""Встречи: занятость пользователей, приглашения и ответы на них."""
import datetime

from django.db import transaction
from django.db.models import Q

from .models import BotUser, Meeting, MeetingParticipant, MeetingStatus
from .services import CalendarError, parse_date, parse_time

DEFAULT_DURATION = 60


def user_meetings(user):
    """Все встречи пользователя: где он организатор или участник."""
    return (
        Meeting.objects.filter(Q(organizer=user) | Q(participants=user))
        .distinct()
        .select_related("organizer")
        .prefetch_related("invitations__user")
    )


def get_busy_slots(user, date=None):
    """Занятые интервалы пользователя: (начало, конец) всех неотменённых встреч,
    от которых он не отказался."""
    meetings = (
        Meeting.objects.filter(
            Q(organizer=user)
            | Q(invitations__user=user, invitations__status__in=[MeetingStatus.PENDING, MeetingStatus.CONFIRMED])
        )
        .exclude(status=MeetingStatus.CANCELLED)
        .distinct()
    )
    if date is not None:
        # встреча накануне вечером может заходить на этот день
        meetings = meetings.filter(date__range=(date - datetime.timedelta(days=1), date))
    return sorted((meeting.start, meeting.end) for meeting in meetings)


def is_free(user, start, end):
    """Свободен ли пользователь на интервале [start, end)."""
    return all(
        not (start < busy_end and busy_start < end)
        for busy_start, busy_end in get_busy_slots(user, start.date())
    )


def find_user(identifier):
    """Ищет зарегистрированного пользователя по @username или Telegram ID."""
    identifier = identifier.strip().lstrip("@")
    if identifier.isdigit():
        return BotUser.objects.filter(telegram_id=int(identifier)).first()
    return BotUser.objects.filter(username__iexact=identifier).first()


def invite_user(meeting, user):
    """Приглашает пользователя, если он свободен. Встреча переходит в статус «ожидается»."""
    if not is_free(user, meeting.start, meeting.end):
        return False
    MeetingParticipant.objects.create(meeting=meeting, user=user, status=MeetingStatus.PENDING)
    meeting.status = MeetingStatus.PENDING
    meeting.save(update_fields=["status"])
    return True


@transaction.atomic
def create_meeting(organizer, title, date_text, time_text, duration, identifiers):
    """Создаёт встречу и приглашает участников.

    Возвращает (встреча, приглашённые, список проблем). Если пригласить
    не удалось никого, встреча не создаётся и выбрасывается CalendarError.
    """
    date, time = parse_date(date_text), parse_time(time_text)
    if duration <= 0:
        raise CalendarError("Длительность должна быть больше нуля.")
    start = datetime.datetime.combine(date, time)
    end = start + datetime.timedelta(minutes=duration)
    if not is_free(organizer, start, end):
        raise CalendarError("У вас уже есть встреча в это время.")

    meeting = Meeting.objects.create(
        organizer=organizer, title=title, date=date, time=time, duration_minutes=duration
    )
    invited, problems = [], []
    for identifier in identifiers:
        user = find_user(identifier)
        if user is None:
            problems.append(f"{identifier} — не зарегистрирован в боте")
        elif user == organizer:
            problems.append(f"{identifier} — это вы")
        elif user in invited:
            continue
        elif invite_user(meeting, user):
            invited.append(user)
        else:
            problems.append(f"{identifier} — занят в это время")

    if not invited:
        transaction.set_rollback(True)
        raise CalendarError("Никого не удалось пригласить:\n" + "\n".join(problems))
    return meeting, invited, problems


def respond_to_meeting(meeting_id, user, accept):
    """Участник принимает или отклоняет приглашение. Возвращает обновлённую встречу."""
    try:
        invitation = MeetingParticipant.objects.select_related("meeting").get(
            meeting_id=meeting_id, user=user
        )
    except MeetingParticipant.DoesNotExist:
        raise CalendarError("Вас нет среди участников этой встречи.")
    meeting = invitation.meeting
    if meeting.status == MeetingStatus.CANCELLED:
        raise CalendarError("Встреча уже отменена.")
    if invitation.status != MeetingStatus.PENDING:
        raise CalendarError("Вы уже ответили на это приглашение.")

    invitation.status = MeetingStatus.CONFIRMED if accept else MeetingStatus.CANCELLED
    invitation.save(update_fields=["status"])
    update_meeting_status(meeting)
    return meeting


def update_meeting_status(meeting):
    """Все приняли — встреча подтверждена, кто-то отказался — отменена, иначе ожидается."""
    statuses = set(meeting.invitations.values_list("status", flat=True))
    if MeetingStatus.CANCELLED in statuses:
        meeting.status = MeetingStatus.CANCELLED
    elif statuses == {MeetingStatus.CONFIRMED}:
        meeting.status = MeetingStatus.CONFIRMED
    else:
        meeting.status = MeetingStatus.PENDING
    meeting.save(update_fields=["status"])
