"""Сбор статистики. Счётчики увеличиваются через F(), чтобы одновременные запросы не затирали друг друга."""
from django.db.models import F
from django.utils import timezone

from .models import BotStatistics


def increment(field):
    """Увеличивает на 1 счётчик field в статистике за сегодня."""
    today = timezone.localdate()
    BotStatistics.objects.get_or_create(date=today)
    BotStatistics.objects.filter(date=today).update(**{field: F(field) + 1})


def track_new_user():
    increment("user_count")


def track_event_created():
    increment("event_count")


def track_event_edited():
    increment("edited_events")


def track_event_cancelled():
    increment("cancelled_events")
