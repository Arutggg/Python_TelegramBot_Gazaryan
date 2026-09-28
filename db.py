import psycopg2

from secrets import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER

# Запросы идемпотентны: их можно выполнять при каждом запуске,
# а базу, созданную в задании 5, они доведут до новой схемы.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id bigint PRIMARY KEY,
    username text,
    first_name text,
    registered_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
    id serial PRIMARY KEY,
    name text NOT NULL,
    date date NOT NULL,
    time time NOT NULL,
    details text NOT NULL DEFAULT ''
);

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS user_id bigint
    REFERENCES users (telegram_id) ON DELETE CASCADE;

-- У одного пользователя не может быть двух событий с одинаковым названием
CREATE UNIQUE INDEX IF NOT EXISTS events_user_id_name_idx ON events (user_id, name);
"""


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db(conn):
    """Создаёт таблицы, если их ещё нет."""
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(SCHEMA)
