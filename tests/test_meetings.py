import datetime

import pytest

from calendar_app.meetings import create_meeting, get_busy_slots, respond_to_meeting
from calendar_app.models import BotUser, Meeting, MeetingStatus
from calendar_app.services import CalendarError


@pytest.fixture
def users(db):
    return {
        name: BotUser.objects.create(telegram_id=tid, username=name)
        for tid, name in [(1, "alice"), (2, "bob"), (3, "carol")]
    }


def test_busy_slots(users):
    create_meeting(users["alice"], "Созвон", "01.10.2026", "10:00", 30, ["@bob"])
    slot = (datetime.datetime(2026, 10, 1, 10, 0), datetime.datetime(2026, 10, 1, 10, 30))
    assert get_busy_slots(users["alice"]) == [slot]
    assert get_busy_slots(users["bob"]) == [slot]
    assert get_busy_slots(users["carol"]) == []


def test_busy_participant_is_not_invited(users):
    create_meeting(users["alice"], "Первая", "01.10.2026", "10:00", 60, ["bob"])
    with pytest.raises(CalendarError, match="занят"):
        create_meeting(users["carol"], "Вторая", "01.10.2026", "10:30", 60, ["bob"])
    assert Meeting.objects.count() == 1  # неудачная встреча не сохранилась

    meeting, invited, problems = create_meeting(
        users["carol"], "Третья", "01.10.2026", "11:00", 60, ["bob", "nobody"]
    )
    assert invited == [users["bob"]]  # встреча вплотную после предыдущей — можно
    assert problems == ["nobody — не зарегистрирован в боте"]
    assert meeting.status == MeetingStatus.PENDING


def test_organizer_must_be_free(users):
    create_meeting(users["alice"], "Первая", "01.10.2026", "10:00", 60, ["bob"])
    with pytest.raises(CalendarError, match="У вас уже есть встреча"):
        create_meeting(users["alice"], "Вторая", "01.10.2026", "10:15", 15, ["carol"])


def test_meeting_status_flow(users):
    meeting, _, _ = create_meeting(users["alice"], "Встреча", "01.10.2026", "10:00", 60, ["bob", "carol"])
    assert respond_to_meeting(meeting.id, users["bob"], accept=True).status == MeetingStatus.PENDING
    assert respond_to_meeting(meeting.id, users["carol"], accept=True).status == MeetingStatus.CONFIRMED
    with pytest.raises(CalendarError, match="уже ответили"):
        respond_to_meeting(meeting.id, users["carol"], accept=False)


def test_declined_meeting_is_cancelled_and_frees_time(users):
    meeting, _, _ = create_meeting(users["alice"], "Встреча", "01.10.2026", "10:00", 60, ["bob"])
    assert respond_to_meeting(meeting.id, users["bob"], accept=False).status == MeetingStatus.CANCELLED
    assert get_busy_slots(users["bob"]) == []
    assert get_busy_slots(users["alice"]) == []


def test_meeting_dialog_and_invitation(tg):
    tg.register(1, username="alice")
    tg.register(2, username="bob")
    for text in ["/meeting", "Планёрка", "01.10.2026", "10:00", "/skip"]:
        tg.send(1, text, username="alice")
    reply = tg.send(1, "@bob @ghost", username="alice")
    assert "Встреча создана" in reply and "@ghost — не зарегистрирован" in reply

    # Боб получил приглашение с кнопками
    assert "приглашает вас" in tg.last_to(2)
    meeting = Meeting.objects.get()
    assert tg.buttons_to(2) == [f"meeting:accept:{meeting.id}", f"meeting:decline:{meeting.id}"]

    assert "Вы приняли" in tg.press(2, f"meeting:accept:{meeting.id}")
    assert "принял(а)" in tg.last_to(1)  # организатора уведомили
    meeting.refresh_from_db()
    assert meeting.status == MeetingStatus.CONFIRMED
    assert "Подтверждена" in tg.send(1, "/meetings")

    # Посторонний не может ответить за участника
    tg.register(3)
    assert "нет среди участников" in tg.press(3, f"meeting:decline:{meeting.id}")
