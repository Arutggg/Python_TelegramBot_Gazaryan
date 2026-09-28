from django.contrib import admin
from django.db.models import Count

from .models import BotStatistics, BotUser, Event, Meeting, MeetingParticipant


class EventInline(admin.TabularInline):
    model = Event
    extra = 0
    fields = ("name", "date", "time", "details", "is_public")


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id", "username", "first_name", "registered_at",
        "event_total", "events_created", "events_edited", "events_cancelled",
    )
    search_fields = ("telegram_id", "username", "first_name")
    readonly_fields = ("registered_at", "events_created", "events_edited", "events_cancelled")
    inlines = [EventInline]

    @admin.display(description="Событий сейчас", ordering="event_total")
    def event_total(self, user):
        return user.event_total

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(event_total=Count("events"))


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "date", "time", "is_public")
    list_filter = ("is_public", "date")
    search_fields = ("name", "details", "owner__username")
    list_select_related = ("owner",)


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ("date", "user_count", "event_count", "edited_events", "cancelled_events")
    date_hierarchy = "date"


class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "date", "time", "duration_minutes", "status", "participant_list")
    list_filter = ("status", "date")
    search_fields = ("title", "organizer__username")
    list_select_related = ("organizer",)
    inlines = [MeetingParticipantInline]

    @admin.display(description="Участники")
    def participant_list(self, meeting):
        return ", ".join(str(invitation) for invitation in meeting.invitations.all())

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("invitations__user")
