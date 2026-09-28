FROM postgres:16-alpine

# Скрипты из /docker-entrypoint-initdb.d выполняются один раз — при первом запуске
# с пустым томом данных. Имя базы, пользователь и пароль задаются через
# переменные POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.
COPY docker/db/init.sh /docker-entrypoint-initdb.d/init.sh
