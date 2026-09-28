from rest_framework import permissions, viewsets

from calendar_app import stats
from calendar_app.models import BotStatistics, BotUser, Event, Meeting

from .serializers import (
    BotStatisticsSerializer,
    BotUserSerializer,
    EventSerializer,
    MeetingSerializer,
    PublicEventSerializer,
)


class BotUserViewSet(viewsets.ModelViewSet):
    """Пользователи бота."""

    queryset = BotUser.objects.all()
    serializer_class = BotUserSerializer
    lookup_field = "telegram_id"


class EventViewSet(viewsets.ModelViewSet):
    """События. Фильтры: ?owner=<telegram_id>, ?is_public=true|false, ?date=ГГГГ-ММ-ДД."""

    serializer_class = EventSerializer

    def get_queryset(self):
        events = Event.objects.select_related("owner")
        params = self.request.query_params
        if "owner" in params:
            events = events.filter(owner__telegram_id=params["owner"])
        if "is_public" in params:
            events = events.filter(is_public=params["is_public"].lower() in ("1", "true"))
        if "date" in params:
            events = events.filter(date=params["date"])
        return events

    # Изменения через API тоже попадают в статистику
    def perform_create(self, serializer):
        event = serializer.save()
        stats.track_event_created(event.owner)

    def perform_update(self, serializer):
        event = serializer.save()
        stats.track_event_edited(event.owner)

    def perform_destroy(self, event):
        owner = event.owner
        event.delete()
        stats.track_event_cancelled(owner)


class MeetingViewSet(viewsets.ReadOnlyModelViewSet):
    """Встречи (только чтение: встречи создаются в боте, где проверяется занятость участников)."""

    queryset = Meeting.objects.select_related("organizer").prefetch_related("invitations__user")
    serializer_class = MeetingSerializer


class BotStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """Статистика по дням."""

    queryset = BotStatistics.objects.all()
    serializer_class = BotStatisticsSerializer
    lookup_field = "date"


class PublicEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Публичные события — доступны всем без авторизации."""

    queryset = Event.objects.filter(is_public=True).select_related("owner")
    serializer_class = PublicEventSerializer
    permission_classes = [permissions.AllowAny]
