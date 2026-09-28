import os
import sys
import types

import psycopg2
import pytest

# Тестовая база берётся из переменных окружения, чтобы не трогать рабочую.
TEST_DB = {
    "host": os.getenv("TEST_DB_HOST", "localhost"),
    "database": os.getenv("TEST_DB_NAME", "calendar_bot_test"),
    "user": os.getenv("TEST_DB_USER", "postgres"),
    "password": os.getenv("TEST_DB_PASSWORD", "postgres"),
}

# Код импортирует настройки из secrets.py, которого нет в репозитории.
# Подменяем его модулем с тестовыми значениями (сохраняя функции stdlib secrets).
import secrets as _stdlib_secrets  # noqa: E402

fake_secrets = types.ModuleType("secrets")
fake_secrets.__dict__.update(vars(_stdlib_secrets))
fake_secrets.__dict__.update(
    API_TOKEN="123456:TEST-TOKEN",
    DB_HOST=TEST_DB["host"],
    DB_NAME=TEST_DB["database"],
    DB_USER=TEST_DB["user"],
    DB_PASSWORD=TEST_DB["password"],
)
sys.modules["secrets"] = fake_secrets

from db import init_db  # noqa: E402


@pytest.fixture
def conn():
    try:
        connection = psycopg2.connect(**TEST_DB)
    except psycopg2.OperationalError as error:
        pytest.skip(f"Тестовая база недоступна: {error}")
    with connection, connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS events, users")
    init_db(connection)
    yield connection
    connection.close()
