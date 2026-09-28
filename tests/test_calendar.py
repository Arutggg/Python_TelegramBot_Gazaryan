import pytest

from event_calendar import INVALID_DATETIME, NOT_FOUND, Calendar
from users import Users

ALICE, BOB = 111, 222


@pytest.fixture
def calendar(conn):
    users = Users(conn)
    users.register(ALICE, "alice", "Alice")
    users.register(BOB, "bob", "Bob")
    return Calendar(conn)


def test_register_twice(conn):
    users = Users(conn)
    assert users.register(ALICE) is True
    assert users.register(ALICE) is False
    assert users.is_registered(ALICE)
    assert not users.is_registered(BOB)


def test_create_and_read(calendar):
    assert "создано" in calendar.create_event(ALICE, "ДР", "12.10.2026", "18:00", "торт")
    assert calendar.read_event(ALICE, "ДР") == "📌 ДР — 12.10.2026 в 18:00\nторт"


def test_create_duplicate(calendar):
    calendar.create_event(ALICE, "ДР", "12.10.2026", "18:00")
    assert "уже есть" in calendar.create_event(ALICE, "ДР", "13.10.2026", "10:00")


@pytest.mark.parametrize("date, time", [("32.10.2026", "18:00"), ("12.10.2026", "25:00"), ("завтра", "утром")])
def test_create_invalid_datetime(calendar, date, time):
    assert calendar.create_event(ALICE, "x", date, time) == INVALID_DATETIME


def test_edit_keeps_unchanged_fields(calendar):
    calendar.create_event(ALICE, "ДР", "12.10.2026", "18:00", "торт")
    calendar.edit_event(ALICE, "ДР", new_date="13.10.2026")
    assert calendar.read_event(ALICE, "ДР") == "📌 ДР — 13.10.2026 в 18:00\nторт"
    calendar.edit_event(ALICE, "ДР", new_description="два торта", new_time="19:30")
    assert calendar.read_event(ALICE, "ДР") == "📌 ДР — 13.10.2026 в 19:30\nдва торта"


def test_delete(calendar):
    calendar.create_event(ALICE, "ДР", "12.10.2026", "18:00")
    assert "удалено" in calendar.delete_event(ALICE, "ДР")
    assert calendar.delete_event(ALICE, "ДР") == NOT_FOUND


def test_display_sorted_by_datetime(calendar):
    assert calendar.display_events(ALICE) == "Событий пока нет."
    calendar.create_event(ALICE, "Позже", "12.10.2026", "18:00")
    calendar.create_event(ALICE, "Раньше", "12.10.2026", "09:00")
    text = calendar.display_events(ALICE)
    assert text.index("Раньше") < text.index("Позже")


def test_users_are_isolated(calendar):
    calendar.create_event(ALICE, "Секрет", "12.10.2026", "18:00")
    # Боб не видит, не меняет и не удаляет событие Алисы
    assert calendar.read_event(BOB, "Секрет") == NOT_FOUND
    assert calendar.edit_event(BOB, "Секрет", new_description="взлом") == NOT_FOUND
    assert calendar.delete_event(BOB, "Секрет") == NOT_FOUND
    assert calendar.display_events(BOB) == "Событий пока нет."
    # А может создать своё событие с тем же названием
    assert "создано" in calendar.create_event(BOB, "Секрет", "01.01.2027", "00:00")
    assert "12.10.2026" in calendar.read_event(ALICE, "Секрет")
