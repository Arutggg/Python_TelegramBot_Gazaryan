"""Юнит-тесты бизнес-логики календаря (без бота)."""
import datetime

import pytest
from django.core import signing
from django.core.management import CommandError, call_command

from calendar_app import tokens
from calendar_app.meetings import create_meeting, get_busy_slots
from calendar_app.models import BotUser, Event
from calendar_app.services import Calendar, CalendarError, parse_date, parse_time, register_user


@pytest.fixture
def calendar(db):
    user, _ = register_user(1, "alice", "Alice")
    return Calendar(user)


def test_create_event(calendar):
    event = calendar.create_event("ДР", "12.10.2026", "18:00", "торт")
    saved = Event.objects.get(pk=event.pk)
    assert (saved.name, saved.date, saved.time, saved.details) == (
        "ДР", datetime.date(2026, 10, 12), datetime.time(18, 0), "торт"
    )
    assert saved.owner == calendar.user


@pytest.mark.parametrize("date, time", [("32.10.2026", "18:00"), ("12.10.2026", "25:00"), ("завтра", "утром")])
def test_create_event_invalid_datetime(calendar, date, time):
    with pytest.raises(CalendarError):
        calendar.create_event("x", date, time)
    assert not Event.objects.exists()


def test_create_duplicate_event(calendar):
    calendar.create_event("ДР", "12.10.2026", "18:00")
    with pytest.raises(CalendarError, match="уже есть"):
        calendar.create_event("ДР", "13.10.2026", "10:00")


def test_edit_keeps_unchanged_fields(calendar):
    calendar.create_event("ДР", "12.10.2026", "18:00", "торт")
    event = calendar.edit_event("ДР", new_date="13.10.2026")
    assert (event.date, event.time, event.details) == (datetime.date(2026, 10, 13), datetime.time(18, 0), "торт")


def test_edit_and_delete_missing_event(calendar):
    with pytest.raises(CalendarError):
        calendar.edit_event("нет", new_description="x")
    with pytest.raises(CalendarError):
        calendar.delete_event("нет")


def test_events_sorted_by_datetime(calendar):
    calendar.create_event("Позже", "12.10.2026", "18:00")
    calendar.create_event("Раньше", "12.10.2026", "09:00")
    calendar.create_event("Вчера", "11.10.2026", "23:00")
    assert [event.name for event in calendar.display_events()] == ["Вчера", "Раньше", "Позже"]


def test_parse_helpers():
    assert parse_date(" 01.02.2027 ") == datetime.date(2027, 2, 1)
    assert parse_time("7:05") == datetime.time(7, 5)


def test_register_user_is_idempotent(db):
    assert register_user(5, "u", "U")[1] is True
    assert register_user(5, "u", "U")[1] is False
    assert BotUser.objects.count() == 1


def test_meeting_crossing_midnight_blocks_next_day(db):
    alice, _ = register_user(1, "alice")
    bob, _ = register_user(2, "bob")
    create_meeting(alice, "Ночной созвон", "01.10.2026", "23:30", 60, ["bob"])
    assert get_busy_slots(bob, datetime.date(2026, 10, 2)) == [
        (datetime.datetime(2026, 10, 1, 23, 30), datetime.datetime(2026, 10, 2, 0, 30))
    ]
    carol, _ = register_user(3, "carol")
    with pytest.raises(CalendarError, match="занят"):
        create_meeting(carol, "Утро", "02.10.2026", "00:00", 15, ["bob"])


def test_expired_cabinet_token(db, monkeypatch):
    user, _ = register_user(1, "alice")
    token = tokens.make_token(user)
    assert tokens.user_from_token(token) == user
    monkeypatch.setattr(tokens, "MAX_AGE", -1)
    assert tokens.user_from_token(token) is None
    assert tokens.user_from_token(signing.dumps(1, salt="другая соль")) is None


def test_runbot_requires_token(settings):
    settings.TELEGRAM_BOT_TOKEN = ""
    with pytest.raises(CommandError, match="TELEGRAM_BOT_TOKEN"):
        call_command("runbot")
