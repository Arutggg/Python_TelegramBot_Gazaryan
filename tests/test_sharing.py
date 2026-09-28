from calendar_app.models import Event


def test_share_by_command(tg):
    tg.register(1, username="alice")
    tg.register(2, username="bob")
    tg.create_event(1, "Концерт", "05.10.2026", "19:00")
    tg.create_event(1, "Личное")

    assert "Общих событий нет" in tg.send(2, "/shared")
    assert "видят другие" in tg.send(1, "/share Концерт")

    reply = tg.send(2, "/shared")
    assert "Концерт" in reply and "@alice" in reply and "Личное" not in reply
    assert "Концерт" in tg.send(2, "/shared @alice")
    assert "Общие события" in tg.send(2, "/calendar") and "Концерт" in tg.send(2, "/calendar")

    assert "скрыто" in tg.send(1, "/unshare Концерт")
    assert "Концерт" not in tg.send(2, "/shared")


def test_share_by_button(tg):
    tg.register(1)
    tg.create_event(1, "Концерт")
    event = Event.objects.get()
    tg.send(1, "/share")
    assert tg.buttons_to(1) == [f"share:{event.id}"]

    assert tg.press(1, f"share:{event.id}") == "Теперь видят все"
    event.refresh_from_db()
    assert event.is_public
    assert tg.press(1, f"share:{event.id}") == "Скрыто"


def test_cannot_share_someone_elses_event(tg):
    tg.register(1)
    tg.register(2)
    tg.create_event(1, "Чужое")
    event = Event.objects.get()
    assert tg.press(2, f"share:{event.id}") == "Событие не найдено."
    assert "нет" in tg.send(2, "/share Чужое")
    event.refresh_from_db()
    assert not event.is_public


def test_shared_events_in_cabinet(tg, client):
    tg.register(1, username="alice")
    tg.register(2, username="bob")
    tg.create_event(1, "Концерт")
    tg.send(1, "/share Концерт")
    link = tg.send(2, "/login").split("\n")[-1]
    page = client.get(link.split("8000", 1)[1]).content.decode()
    assert "Общие события" in page and "Концерт" in page
