#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput -v 0

# Суперпользователь создаётся автоматически, если заданы переменные
# DJANGO_SUPERUSER_USERNAME и DJANGO_SUPERUSER_PASSWORD (и его ещё нет)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null \
        && echo "Суперпользователь $DJANGO_SUPERUSER_USERNAME создан" \
        || echo "Суперпользователь $DJANGO_SUPERUSER_USERNAME уже есть"
fi

exec "$@"
