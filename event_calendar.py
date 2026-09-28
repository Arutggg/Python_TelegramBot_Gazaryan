import datetime

DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"
INVALID_DATETIME = "Неверная дата или время. Формат: ДД.ММ.ГГГГ и ЧЧ:ММ."


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
    """Календарь событий. События хранятся в таблице events PostgreSQL."""

    def __init__(self, conn):
        self.conn = conn

    def _execute(self, query, params=()):
        """Выполняет запрос в транзакции и возвращает курсор с результатом."""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor

    def _exists(self, event_name):
        cursor = self._execute("SELECT 1 FROM events WHERE name = %s", (event_name,))
        return cursor.fetchone() is not None

    def create_event(self, event_name, event_date, event_time, event_details=""):
        try:
            date, time = parse_date(event_date), parse_time(event_time)
        except ValueError:
            return INVALID_DATETIME
        if self._exists(event_name):
            return f"Событие «{event_name}» уже есть."
        self._execute(
            "INSERT INTO events (name, date, time, details) VALUES (%s, %s, %s, %s)",
            (event_name, date, time, event_details),
        )
        return f"Событие «{event_name}» создано."

    def read_event(self, event_name):
        cursor = self._execute(
            "SELECT name, date, time, details FROM events WHERE name = %s",
            (event_name,),
        )
        row = cursor.fetchone()
        return format_event(*row) if row else "Такого события нет."

    def edit_event(self, event_name, new_date=None, new_description=None, new_time=None):
        if not self._exists(event_name):
            return "Такого события нет."
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
            WHERE name = %s
            """,
            (date, time, new_description, event_name),
        )
        return f"Событие «{event_name}» обновлено."

    def delete_event(self, event_name):
        cursor = self._execute("DELETE FROM events WHERE name = %s", (event_name,))
        if cursor.rowcount == 0:
            return "Такого события нет."
        return f"Событие «{event_name}» удалено."

    def display_events(self):
        cursor = self._execute(
            "SELECT name, date, time, details FROM events ORDER BY date, time"
        )
        rows = cursor.fetchall()
        if not rows:
            return "Событий пока нет."
        return "Ваши события:\n\n" + "\n\n".join(format_event(*row) for row in rows)
