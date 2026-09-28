import datetime

DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"
INVALID_DATETIME = "Неверная дата или время. Формат: ДД.ММ.ГГГГ и ЧЧ:ММ."
NOT_FOUND = "Такого события нет."


def parse_date(text):
    return datetime.datetime.strptime(text.strip(), DATE_FORMAT).date()


def parse_time(text):
    return datetime.datetime.strptime(text.strip(), TIME_FORMAT).time()


def format_event(name, date, time, details):
    text = f"📌 {name} — {date.strftime(DATE_FORMAT)} в {time.strftime(TIME_FORMAT)}"
    if details:
        text += f"\n{details}"
    return text


class Calendar:
    """Календарь событий в PostgreSQL.

    Каждый метод принимает user_id (идентификатор пользователя в Telegram)
    и работает только с событиями этого пользователя.
    """

    def __init__(self, conn):
        self.conn = conn

    def _execute(self, query, params=()):
        """Выполняет запрос в транзакции и возвращает курсор с результатом."""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor

    def event_exists(self, user_id, event_name):
        cursor = self._execute(
            "SELECT 1 FROM events WHERE user_id = %s AND name = %s",
            (user_id, event_name),
        )
        return cursor.fetchone() is not None

    def create_event(self, user_id, event_name, event_date, event_time, event_details=""):
        try:
            date, time = parse_date(event_date), parse_time(event_time)
        except ValueError:
            return INVALID_DATETIME
        if self.event_exists(user_id, event_name):
            return f"Событие «{event_name}» уже есть."
        self._execute(
            """
            INSERT INTO events (user_id, name, date, time, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, event_name, date, time, event_details),
        )
        return f"Событие «{event_name}» создано."

    def read_event(self, user_id, event_name):
        cursor = self._execute(
            "SELECT name, date, time, details FROM events WHERE user_id = %s AND name = %s",
            (user_id, event_name),
        )
        row = cursor.fetchone()
        return format_event(*row) if row else NOT_FOUND

    def edit_event(self, user_id, event_name, new_date=None, new_description=None, new_time=None):
        if not self.event_exists(user_id, event_name):
            return NOT_FOUND
        try:
            date = parse_date(new_date) if new_date else None
            time = parse_time(new_time) if new_time else None
        except ValueError:
            return INVALID_DATETIME
        # COALESCE оставляет старое значение, если новое не передано (NULL)
        self._execute(
            """
            UPDATE events
            SET date = COALESCE(%s, date),
                time = COALESCE(%s, time),
                details = COALESCE(%s, details)
            WHERE user_id = %s AND name = %s
            """,
            (date, time, new_description, user_id, event_name),
        )
        return f"Событие «{event_name}» обновлено."

    def delete_event(self, user_id, event_name):
        cursor = self._execute(
            "DELETE FROM events WHERE user_id = %s AND name = %s",
            (user_id, event_name),
        )
        if cursor.rowcount == 0:
            return NOT_FOUND
        return f"Событие «{event_name}» удалено."

    def display_events(self, user_id):
        cursor = self._execute(
            """
            SELECT name, date, time, details FROM events
            WHERE user_id = %s
            ORDER BY date, time
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            return "Событий пока нет."
        return "Ваши события:\n\n" + "\n\n".join(format_event(*row) for row in rows)
