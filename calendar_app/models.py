from django.db import models


class BotUser(models.Model):
    """Пользователь Telegram-бота."""

    telegram_id = models.BigIntegerField("Telegram ID", unique=True)
    username = models.CharField("Username", max_length=64, blank=True)
    first_name = models.CharField("Имя", max_length=255, blank=True)
    registered_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-registered_at"]

    def __str__(self):
        return f"@{self.username}" if self.username else f"{self.first_name} ({self.telegram_id})"


class Event(models.Model):
    """Событие в календаре пользователя."""

    owner = models.ForeignKey(
        BotUser, on_delete=models.CASCADE, related_name="events", verbose_name="Владелец"
    )
    name = models.CharField("Название", max_length=255)
    date = models.DateField("Дата")
    time = models.TimeField("Время")
    details = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["date", "time"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_event_name_per_owner"),
        ]

    def __str__(self):
        return f"{self.name} — {self.date:%d.%m.%Y} {self.time:%H:%M}"


class BotStatistics(models.Model):
    """Статистика работы бота за день."""

    date = models.DateField("Дата", unique=True)
    user_count = models.PositiveIntegerField("Новых пользователей", default=0)
    event_count = models.PositiveIntegerField("Создано событий", default=0)
    edited_events = models.PositiveIntegerField("Изменено событий", default=0)
    cancelled_events = models.PositiveIntegerField("Отменено событий", default=0)

    class Meta:
        verbose_name = "Статистика за день"
        verbose_name_plural = "Статистика"
        ordering = ["-date"]

    def __str__(self):
        return f"Статистика за {self.date:%d.%m.%Y}"
