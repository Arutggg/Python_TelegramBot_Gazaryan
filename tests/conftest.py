import datetime

import pytest
from telegram import CallbackQuery, Chat, Message, MessageEntity, Update, User

from bot.app import create_updater


class FakeTelegram:
    """Отправляет боту сообщения от имени пользователей и собирает ответы. В Telegram не ходит."""

    def __init__(self):
        self.updater = create_updater(token="123456:TEST-TOKEN")
        self.bot = self.updater.bot
        self.bot._bot = User(1, "Calendar", True, username="calendar_test_bot")
        self.sent = []  # все сообщения, отправленные ботом: (chat_id, text, kwargs)
        self.bot.send_message = self._send_message
        self.bot.answer_callback_query = self._answer_callback_query
        self.bot.edit_message_text = self._edit_message_text
        self.bot.edit_message_reply_markup = self._edit_message_reply_markup
        self.alerts = []  # всплывающие ответы на нажатия кнопок
        self.update_id = 0

    def _send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))

    def _answer_callback_query(self, callback_query_id, text=None, **kwargs):
        if text:
            self.alerts.append(text)
        return True

    def _edit_message_text(self, text, chat_id=None, message_id=None, **kwargs):
        self.sent.append((chat_id, text, kwargs))

    def _edit_message_reply_markup(self, chat_id=None, message_id=None, reply_markup=None, **kwargs):
        self.sent.append((chat_id, "(обновлены кнопки)", {"reply_markup": reply_markup}))

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

    def press(self, user_id, callback_data):
        """Нажимает инлайн-кнопку с callback_data от имени пользователя."""
        user = User(user_id, f"User{user_id}", False, username=f"user{user_id}")
        message = Message(
            self._next_id(), datetime.datetime.now(), Chat(user_id, Chat.PRIVATE),
            text="кнопки", bot=self.bot,
        )
        query = CallbackQuery(
            str(self.update_id), user, "chat", message=message, data=callback_data, bot=self.bot
        )
        self.sent.clear()
        self.alerts.clear()
        self.updater.dispatcher.process_update(Update(self.update_id, callback_query=query))
        return self.alerts[-1] if self.alerts else self.last_to(user_id)

    def buttons_to(self, chat_id):
        """callback_data всех кнопок в сообщениях, отправленных пользователю."""
        return [
            button.callback_data
            for cid, _, kwargs in self.sent
            if cid == chat_id and kwargs.get("reply_markup")
            for row in kwargs["reply_markup"].inline_keyboard
            for button in row
        ]

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
