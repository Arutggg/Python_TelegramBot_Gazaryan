import pytest
from rest_framework.test import APIClient

from calendar_app.models import BotStatistics, BotUser, Event


@pytest.fixture
def api(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


@pytest.fixture
def alice(db):
    return BotUser.objects.create(telegram_id=111, username="alice")


def test_api_requires_admin(db, alice):
    anonymous = APIClient()
    assert anonymous.get("/api/events/").status_code == 403
    assert anonymous.get("/api/users/").status_code == 403


def test_event_crud(api, alice):
    response = api.post("/api/events/", {"owner": 111, "name": "Созвон", "date": "2026-10-01", "time": "10:00"})
    assert response.status_code == 201, response.data
    event_id = response.data["id"]

    assert api.get("/api/events/?owner=111").data["results"][0]["name"] == "Созвон"
    assert api.patch(f"/api/events/{event_id}/", {"details": "Zoom"}).data["details"] == "Zoom"
    assert api.delete(f"/api/events/{event_id}/").status_code == 204
    assert not Event.objects.exists()

    stats = BotStatistics.objects.get()
    assert (stats.event_count, stats.edited_events, stats.cancelled_events) == (1, 1, 1)


def test_event_validation(api, alice):
    api.post("/api/events/", {"owner": 111, "name": "A", "date": "2026-10-01", "time": "10:00"})
    duplicate = api.post("/api/events/", {"owner": 111, "name": "A", "date": "2026-10-02", "time": "10:00"})
    assert duplicate.status_code == 400
    unknown_owner = api.post("/api/events/", {"owner": 999, "name": "B", "date": "2026-10-01", "time": "10:00"})
    assert unknown_owner.status_code == 400


def test_public_events_open_to_everyone(db, alice):
    Event.objects.create(owner=alice, name="Концерт", date="2026-10-05", time="19:00", is_public=True)
    Event.objects.create(owner=alice, name="Личное", date="2026-10-05", time="20:00")
    data = APIClient().get("/api/public-events/").data["results"]
    assert [event["name"] for event in data] == ["Концерт"]
    assert data[0]["owner"] == "@alice"


def test_meetings_and_statistics(api, tg):
    tg.register(1, username="alice")
    tg.register(2, username="bob")
    for text in ["/meeting", "Планёрка", "01.10.2026", "10:00", "/skip", "@bob"]:
        tg.send(1, text, username="alice")
    meeting = api.get("/api/meetings/").data["results"][0]
    assert meeting["organizer"] == 1
    assert meeting["participants"] == [{"telegram_id": 2, "username": "bob", "status": "pending"}]
    assert api.post("/api/meetings/", {}).status_code == 405  # только чтение
    assert api.get("/api/statistics/").data["results"][0]["user_count"] == 2


def test_browsable_api(admin_client):
    page = admin_client.get("/api/", HTTP_ACCEPT="text/html")
    assert page.status_code == 200
    assert "Django REST framework" in page.content.decode()
    assert "/api/events/" in page.content.decode()
