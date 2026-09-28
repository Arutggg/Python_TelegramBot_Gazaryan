from django.contrib import admin

from .models import BotUser, Event


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
