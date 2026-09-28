import csv
import io
import json

import pytest
from django.urls import reverse

import bot.app
from calendar_app.models import BotUser
from calendar_app.tokens import make_token


@pytest.fixture
def web(client, monkeypatch):
    """Бот ходит на эндпоинт выгрузки через тестовый клиент Django вместо сети."""
    requested = []

    def fake_download(url):
        requested.append(url)
        response = client.get(url.split("8000", 1)[1])
        assert response.status_code == 200
        return response.content

    monkeypatch.setattr(bot.app, "download_export", fake_download)
    return requested


def export_path(telegram_id, file_format):
    token = make_token(BotUser.objects.get(telegram_id=telegram_id))
    return reverse("calendar_app:export", args=[token]) + f"?format={file_format}"


def test_export_csv_and_json(tg, client):
    tg.register(1)
    tg.create_event(1, "ДР", "12.10.2026", "18:00", "торт, свечи")

    response = client.get(export_path(1, "csv"))
    assert response["Content-Disposition"] == 'attachment; filename="events.csv"'
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows == [{"name": "ДР", "date": "12.10.2026", "time": "18:00", "details": "торт, свечи", "is_public": "False"}]

    data = json.loads(client.get(export_path(1, "json")).content)
    assert data == [{"name": "ДР", "date": "12.10.2026", "time": "18:00", "details": "торт, свечи", "is_public": False}]


def test_export_only_own_events(tg, client):
    tg.register(1)
    tg.register(2)
    tg.create_event(1, "Моё")
    tg.create_event(2, "Чужое")
    data = json.loads(client.get(export_path(1, "json")).content)
    assert [row["name"] for row in data] == ["Моё"]


def test_export_bad_token_and_format(tg, client):
    tg.register(1)
    assert client.get(reverse("calendar_app:export", args=["bad-token"])).status_code == 404
    assert client.get(export_path(1, "xml")).status_code == 400


def test_export_from_bot(tg, web):
    tg.register(1)
    tg.create_event(1, "ДР", "12.10.2026", "18:00")
    assert "/export/" in tg.send(1, "/export")
    assert tg.buttons_to(1) == ["export:csv", "export:json"]

    tg.press(1, "export:json")
    assert "/export/" in web[0] and web[0].endswith("format=json")
    chat_id, filename, content = tg.documents[-1]
    assert (chat_id, filename) == (1, "events.json")
    assert json.loads(content)[0]["name"] == "ДР"


def test_export_when_web_is_down(tg, monkeypatch):
    def broken(url):
        raise OSError("connection refused")

    monkeypatch.setattr(bot.app, "download_export", broken)
    tg.register(1)
    assert "недоступно" in tg.press(1, "export:csv")
    assert tg.documents == []
