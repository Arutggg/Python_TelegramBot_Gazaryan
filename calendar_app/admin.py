from django.contrib import admin

from .models import BotStatistics, BotUser, Event


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "registered_at")
    search_fields = ("telegram_id", "username", "first_name")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "date", "time")
    list_filter = ("date",)
    search_fields = ("name", "details", "owner__username")
    list_select_related = ("owner",)


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ("date", "user_count", "event_count", "edited_events", "cancelled_events")
    date_hierarchy = "date"
