"""Сквозные тесты: сообщения проходят через настоящие обработчики бота без обращения к Telegram."""
import datetime

import pytest
from telegram import Chat, Message, MessageEntity, Update, User

from bot import create_updater


class FakeTelegram:
    """Отправляет боту сообщения от имени пользователя и собирает ответы."""

    def __init__(self, conn):
        self.updater = create_updater(conn, token="123456:TEST-TOKEN")
        self.bot = self.updater.bot
        self.bot._bot = User(1, "Calendar", True, username="calendar_test_bot")
        self.replies = []
        self.bot.send_message = self._send_message
        self.update_id = 0

    def _send_message(self, chat_id, text, **kwargs):
        self.replies.append((chat_id, text))

    def send(self, user_id, text):
        self.update_id += 1
        user = User(user_id, f"user{user_id}", False)
        entities = []
        if text.startswith("/"):
            entities = [MessageEntity(MessageEntity.BOT_COMMAND, 0, len(text.split()[0]))]
        message = Message(
            self.update_id, datetime.datetime.now(), Chat(user_id, Chat.PRIVATE),
            from_user=user, text=text, entities=entities, bot=self.bot,
        )
        self.replies.clear()
        self.updater.dispatcher.process_update(Update(self.update_id, message=message))
        return self.replies[-1][1]


@pytest.fixture
def tg(conn):
    return FakeTelegram(conn)


def test_commands_require_registration(tg):
    assert "/register" in tg.send(1, "/create_event")
    assert "/register" in tg.send(1, "/events")
    assert "Готово" in tg.send(1, "/register")
    assert "уже зарегистрированы" in tg.send(1, "/register")


def test_create_event_dialog(tg):
    tg.send(1, "/register")
    assert "назовём" in tg.send(1, "/create_event")
    assert "Дата" in tg.send(1, "ДР мамы")
    assert "Неверная дата" in tg.send(1, "завтра")  # бот остаётся на том же шаге
    assert "Время" in tg.send(1, "12.10.2026")
    assert "Описание" in tg.send(1, "18:00")
    assert "создано" in tg.send(1, "купить цветы")
    assert "купить цветы" in tg.send(1, "/read_event ДР мамы")


def test_create_with_skip_and_cancel(tg):
    tg.send(1, "/register")
    tg.send(1, "/create_event")
    tg.send(1, "Черновик")
    assert "отменено" in tg.send(1, "/cancel")
    assert tg.send(1, "/events") == "Событий пока нет."

    for text in ["/create_event", "Встреча", "01.10.2026", "09:00"]:
        tg.send(1, text)
    assert "создано" in tg.send(1, "/skip")
    assert tg.send(1, "/events") == "Ваши события:\n\n📌 Встреча — 01.10.2026 в 09:00"


def test_edit_dialog(tg):
    tg.send(1, "/register")
    for text in ["/create_event", "ДР", "12.10.2026", "18:00", "торт"]:
        tg.send(1, text)
    tg.send(1, "/edit_event")
    assert "нет" in tg.send(1, "Нет такого")
    tg.send(1, "ДР")
    tg.send(1, "-")
    tg.send(1, "19:30")
    assert "обновлено" in tg.send(1, "два торта")
    assert tg.send(1, "/read_event ДР") == "📌 ДР — 12.10.2026 в 19:30\nдва торта"


def test_delete_asks_name(tg):
    tg.send(1, "/register")
    for text in ["/create_event", "ДР", "12.10.2026", "18:00", "/skip"]:
        tg.send(1, text)
    assert "название" in tg.send(1, "/delete_event")
    assert "удалено" in tg.send(1, "ДР")


def test_dialogs_of_different_users_do_not_mix(tg):
    tg.send(1, "/register")
    tg.send(2, "/register")
    tg.send(1, "/create_event")
    tg.send(2, "/create_event")
    tg.send(1, "Событие Алисы")
    tg.send(2, "Событие Боба")
    for user_id in (1, 2):
        tg.send(user_id, "01.10.2026")
        tg.send(user_id, "10:00")
        tg.send(user_id, "/skip")
    assert "Алисы" in tg.send(1, "/events") and "Боба" not in tg.send(1, "/events")
    assert "Боба" in tg.send(2, "/events") and "Алисы" not in tg.send(2, "/events")


def test_unknown_message(tg):
    assert "/help" in tg.send(1, "привет")
