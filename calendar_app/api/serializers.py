from rest_framework import serializers

from calendar_app.models import BotStatistics, BotUser, Event, Meeting, MeetingParticipant


class BotUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotUser
        fields = [
            "id", "telegram_id", "username", "first_name", "registered_at",
            "events_created", "events_edited", "events_cancelled",
        ]
        read_only_fields = ["registered_at", "events_created", "events_edited", "events_cancelled"]


class EventSerializer(serializers.ModelSerializer):
    # Владелец задаётся Telegram ID, а не внутренним id базы
    owner = serializers.SlugRelatedField(slug_field="telegram_id", queryset=BotUser.objects.all())

    class Meta:
        model = Event
        fields = ["id", "owner", "name", "date", "time", "details", "is_public", "created_at"]
        read_only_fields = ["created_at"]


class PublicEventSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()

    class Meta:
        model = Event
        fields = ["id", "owner", "name", "date", "time", "details"]


class InvitationSerializer(serializers.ModelSerializer):
    telegram_id = serializers.IntegerField(source="user.telegram_id")
    username = serializers.CharField(source="user.username")

    class Meta:
        model = MeetingParticipant
        fields = ["telegram_id", "username", "status"]


class MeetingSerializer(serializers.ModelSerializer):
    organizer = serializers.SlugRelatedField(slug_field="telegram_id", read_only=True)
    participants = InvitationSerializer(source="invitations", many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = [
            "id", "title", "date", "time", "duration_minutes",
            "status", "organizer", "participants", "created_at",
        ]


class BotStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotStatistics
        fields = ["date", "user_count", "event_count", "edited_events", "cancelled_events"]
