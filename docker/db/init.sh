#!/bin/sh
set -e

# Часовой пояс базы по умолчанию и права пользователя на создание баз (нужно для тестов)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
ALTER DATABASE "$POSTGRES_DB" SET timezone TO 'Europe/Moscow';
ALTER USER "$POSTGRES_USER" CREATEDB;
SQL

echo "База $POSTGRES_DB инициализирована"
