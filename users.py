class Users:
    """Учётные записи пользователей бота. Хранятся в таблице users."""

    def __init__(self, conn):
        self.conn = conn

    def register(self, telegram_id, username=None, first_name=None):
        """Регистрирует пользователя. Возвращает False, если он уже был зарегистрирован."""
        with self.conn:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (telegram_id, username, first_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (telegram_id) DO NOTHING
                    """,
                    (telegram_id, username, first_name),
                )
                return cursor.rowcount == 1

    def is_registered(self, telegram_id):
        with self.conn:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM users WHERE telegram_id = %s", (telegram_id,))
                return cursor.fetchone() is not None
