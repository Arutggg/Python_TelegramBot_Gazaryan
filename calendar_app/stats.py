"""Сбор статистики. Счётчики увеличиваются через F(), чтобы одновременные запросы не затирали друг друга."""
from django.db.models import F
from django.utils import timezone

from .models import BotStatistics, BotUser


def increment(field):
    """Увеличивает на 1 счётчик field в статистике за сегодня."""
    today = timezone.localdate()
    BotStatistics.objects.get_or_create(date=today)
    BotStatistics.objects.filter(date=today).update(**{field: F(field) + 1})


def increment_user(user, field):
    """Увеличивает на 1 личный счётчик пользователя."""
    BotUser.objects.filter(pk=user.pk).update(**{field: F(field) + 1})


def track_new_user():
    increment("user_count")


def track_event_created(user):
    increment("event_count")
    increment_user(user, "events_created")


def track_event_edited(user):
    increment("edited_events")
    increment_user(user, "events_edited")


def track_event_cancelled(user):
    increment("cancelled_events")
    increment_user(user, "events_cancelled")
