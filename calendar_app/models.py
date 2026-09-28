import datetime

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


class MeetingStatus(models.TextChoices):
    PENDING = "pending", "Ожидается"
    CONFIRMED = "confirmed", "Подтверждена"
    CANCELLED = "cancelled", "Отменена"


class Meeting(models.Model):
    """Встреча, которую один пользователь назначает другим."""

    organizer = models.ForeignKey(
        BotUser, on_delete=models.CASCADE, related_name="organized_meetings", verbose_name="Организатор"
    )
    title = models.CharField("Тема", max_length=255)
    date = models.DateField("Дата")
    time = models.TimeField("Время")
    duration_minutes = models.PositiveIntegerField("Длительность, мин", default=60)
    participants = models.ManyToManyField(
        BotUser, through="MeetingParticipant", related_name="meetings", verbose_name="Участники"
    )
    status = models.CharField(
        "Статус", max_length=16, choices=MeetingStatus.choices, default=MeetingStatus.PENDING
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Встреча"
        verbose_name_plural = "Встречи"
        ordering = ["date", "time"]

    def __str__(self):
        return f"{self.title} — {self.date:%d.%m.%Y} {self.time:%H:%M}"

    @property
    def start(self):
        return datetime.datetime.combine(self.date, self.time)

    @property
    def end(self):
        return self.start + datetime.timedelta(minutes=self.duration_minutes)


class MeetingParticipant(models.Model):
    """Участник встречи и его ответ на приглашение."""

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="invitations")
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name="invitations")
    status = models.CharField(
        "Ответ", max_length=16, choices=MeetingStatus.choices, default=MeetingStatus.PENDING
    )

    class Meta:
        verbose_name = "Участник встречи"
        verbose_name_plural = "Участники встречи"
        constraints = [
            models.UniqueConstraint(fields=["meeting", "user"], name="unique_meeting_participant"),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_status_display()}"
