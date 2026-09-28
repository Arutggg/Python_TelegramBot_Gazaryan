FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала зависимости: этот слой пересобирается, только если изменился requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x docker/web/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker/web/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
