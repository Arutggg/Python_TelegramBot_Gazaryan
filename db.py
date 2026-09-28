import psycopg2

from secrets import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS events (
    id serial PRIMARY KEY,
    name text NOT NULL,
    date date NOT NULL,
    time time NOT NULL,
    details text NOT NULL DEFAULT ''
);
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
    with conn.cursor() as cursor:
        cursor.execute(CREATE_TABLES)
    conn.commit()
