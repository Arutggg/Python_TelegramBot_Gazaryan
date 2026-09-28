from django.utils import timezone

from calendar_app.models import BotStatistics


def today_stats():
    return BotStatistics.objects.get(date=timezone.localdate())


def test_statistics_are_collected(tg):
    tg.register(1)
    tg.register(2)
    tg.register(2)  # повторная регистрация не считается
    tg.create_event(1, "A")
    tg.create_event(1, "B")
    for text in ["/edit_event", "A", "-", "-", "новое описание"]:
        tg.send(1, text)
    tg.send(1, "/delete_event B")

    stats = today_stats()
    assert (stats.user_count, stats.event_count, stats.edited_events, stats.cancelled_events) == (2, 2, 1, 1)


def test_failed_actions_are_not_counted(tg):
    tg.register(1)
    tg.send(1, "/delete_event нет такого")
    assert today_stats().cancelled_events == 0
