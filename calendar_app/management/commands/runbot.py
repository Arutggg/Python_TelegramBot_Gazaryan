from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bot.app import create_updater


class Command(BaseCommand):
    help = "Запускает Telegram-бота"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("Не задан TELEGRAM_BOT_TOKEN (см. .env.example)")
        updater = create_updater()
        updater.start_polling()
        self.stdout.write(self.style.SUCCESS("Бот запущен"))
        updater.idle()
