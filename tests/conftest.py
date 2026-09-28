import datetime

import pytest
from telegram import Chat, Message, MessageEntity, Update, User

from bot.app import create_updater


class FakeTelegram:
    """Отправляет боту сообщения от имени пользователей и собирает ответы. В Telegram не ходит."""

    def __init__(self):
        self.updater = create_updater(token="123456:TEST-TOKEN")
        self.bot = self.updater.bot
        self.bot._bot = User(1, "Calendar", True, username="calendar_test_bot")
        self.sent = []  # все сообщения, отправленные ботом: (chat_id, text, kwargs)
        self.bot.send_message = self._send_message
        self.update_id = 0

    def _send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))

    def _next_id(self):
        self.update_id += 1
        return self.update_id

    def send(self, user_id, text, username=None):
        """Отправляет сообщение от пользователя и возвращает последний ответ ему."""
        user = User(user_id, f"User{user_id}", False, username=username or f"user{user_id}")
        entities = []
        if text.startswith("/"):
            entities = [MessageEntity(MessageEntity.BOT_COMMAND, 0, len(text.split()[0]))]
        message = Message(
            self._next_id(), datetime.datetime.now(), Chat(user_id, Chat.PRIVATE),
            from_user=user, text=text, entities=entities, bot=self.bot,
        )
        self.sent.clear()
        self.updater.dispatcher.process_update(Update(self.update_id, message=message))
        return self.last_to(user_id)

    def last_to(self, chat_id):
        texts = [text for cid, text, _ in self.sent if cid == chat_id]
        return texts[-1] if texts else None

    def register(self, user_id, username=None):
        self.send(user_id, "/register", username=username)

    def create_event(self, user_id, name, date="01.10.2026", time="10:00", details="/skip"):
        for text in ["/create_event", name, date, time]:
            self.send(user_id, text)
        return self.send(user_id, details)


@pytest.fixture
def tg(db):
    return FakeTelegram()
