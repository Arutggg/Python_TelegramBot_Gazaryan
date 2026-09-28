import re

from django.urls import reverse

from calendar_app.models import BotUser
from calendar_app.services import get_user_events
from calendar_app.tokens import make_token


def cabinet_link(reply):
    return re.search(r"https?://\S+/cabinet/\S+/", reply).group(0)


def test_login_creates_account_and_gives_cabinet_link(tg, client):
    reply = tg.send(1, "/login")
    assert "Учётная запись создана" in reply and "Telegram ID: 1" in reply
    assert "Вы вошли" in tg.send(1, "/login")
    tg.create_event(1, "Мой ДР", "12.10.2026", "18:00")

    path = cabinet_link(tg.send(1, "/login")).split("8000", 1)[1]
    page = client.get(path)
    assert page.status_code == 200
    assert "Мой ДР" in page.content.decode()


def test_cabinet_rejects_forged_token(tg, client):
    tg.register(1)
    tg.create_event(1, "Секрет")
    token = make_token(BotUser.objects.get(telegram_id=1))
    forged = token.replace(token[0], "2" if token[0] != "2" else "3", 1)
    assert client.get(reverse("calendar_app:cabinet", args=[forged])).status_code == 404


def test_calendar_command(tg):
    tg.register(1, username="alice")
    tg.register(2, username="bob")
    tg.create_event(1, "Спортзал", "01.10.2026", "08:00")
    for text in ["/meeting", "Планёрка", "01.10.2026", "10:00", "30", "@bob"]:
        tg.send(1, text, username="alice")
    reply = tg.send(1, "/calendar")
    assert "Спортзал" in reply and "Планёрка" in reply
    assert "Планёрка" in tg.send(2, "/calendar")  # участник видит встречу у себя
    assert "Спортзал" not in tg.send(2, "/calendar")


def test_user_counters(tg):
    tg.register(1)
    tg.create_event(1, "A")
    tg.create_event(1, "B")
    tg.send(1, "/delete_event A")
    user = BotUser.objects.get(telegram_id=1)
    assert (user.events_created, user.events_edited, user.events_cancelled) == (2, 0, 1)
    assert list(get_user_events(1).values_list("name", flat=True)) == ["B"]


def test_admin_pages(tg, admin_client):
    tg.register(1)
    tg.create_event(1, "A")
    for url in ["botuser", "event", "meeting", "botstatistics"]:
        assert admin_client.get(f"/admin/calendar_app/{url}/").status_code == 200
    user = BotUser.objects.get()
    assert admin_client.get(f"/admin/calendar_app/botuser/{user.pk}/change/").status_code == 200
