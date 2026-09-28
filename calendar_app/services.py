"""Бизнес-логика календаря. Бот и веб-приложение работают с данными только через эти функции."""
import datetime

from . import stats
from .models import BotUser, Event

DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"


class CalendarError(Exception):
    """Ошибка с понятным пользователю текстом."""


def parse_date(text):
    try:
        return datetime.datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        raise CalendarError("Неверная дата. Формат: ДД.ММ.ГГГГ, например 25.12.2026.")


def parse_time(text):
    try:
        return datetime.datetime.strptime(text.strip(), TIME_FORMAT).time()
    except ValueError:
        raise CalendarError("Неверное время. Формат: ЧЧ:ММ, например 18:30.")


def register_user(telegram_id, username="", first_name=""):
    """Регистрирует пользователя. Возвращает (пользователь, создан_ли_он_сейчас)."""
    user, created = BotUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={"username": username or "", "first_name": first_name or ""},
    )
    if created:
        stats.track_new_user()
    return user, created


def get_user(telegram_id):
    return BotUser.objects.filter(telegram_id=telegram_id).first()


def get_user_events(telegram_id):
    """События пользователя по его Telegram ID."""
    return Event.objects.filter(owner__telegram_id=telegram_id)


class Calendar:
    """Календарь одного пользователя: создание, чтение, редактирование и удаление событий."""

    def __init__(self, user):
        self.user = user

    def _get(self, event_name):
        try:
            return self.user.events.get(name=event_name)
        except Event.DoesNotExist:
            raise CalendarError(f"События «{event_name}» нет.")

    def event_exists(self, event_name):
        return self.user.events.filter(name=event_name).exists()

    def create_event(self, event_name, event_date, event_time, event_details=""):
        if self.event_exists(event_name):
            raise CalendarError(f"Событие «{event_name}» уже есть.")
        event = Event.objects.create(
            owner=self.user,
            name=event_name,
            date=parse_date(event_date),
            time=parse_time(event_time),
            details=event_details,
        )
        stats.track_event_created(self.user)
        return event

    def read_event(self, event_name):
        return self._get(event_name)

    def edit_event(self, event_name, new_date=None, new_description=None, new_time=None):
        event = self._get(event_name)
        if new_date:
            event.date = parse_date(new_date)
        if new_time:
            event.time = parse_time(new_time)
        if new_description is not None:
            event.details = new_description
        event.save()
        stats.track_event_edited(self.user)
        return event

    def delete_event(self, event_name):
        event = self._get(event_name)
        event.delete()
        stats.track_event_cancelled(self.user)
        return event

    def display_events(self):
        return list(self.user.events.all())
