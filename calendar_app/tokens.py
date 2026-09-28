"""Подписанные ссылки на личный кабинет.

Токен содержит Telegram ID и подписан SECRET_KEY, поэтому подставить в ссылку
чужой ID нельзя. Ссылка действует ограниченное время.
"""
from django.core import signing

from .models import BotUser

SALT = "calendar_app.cabinet"
MAX_AGE = 7 * 24 * 60 * 60  # неделя


def make_token(user):
    return signing.dumps(user.telegram_id, salt=SALT)


def user_from_token(token):
    """Возвращает пользователя по токену или None, если токен неверный или устарел."""
    try:
        telegram_id = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    return BotUser.objects.filter(telegram_id=telegram_id).first()
