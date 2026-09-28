from calendar_app.models import Event


def test_commands_require_registration(tg):
    assert "/register" in tg.send(1, "/create_event")
    assert "/register" in tg.send(1, "/events")
    assert "Готово" in tg.send(1, "/register")
    assert "уже зарегистрированы" in tg.send(1, "/register")


def test_create_event(tg):
    tg.register(1)
    assert "назовём" in tg.send(1, "/create_event")
    assert "Дата" in tg.send(1, "ДР мамы")
    assert "Неверная дата" in tg.send(1, "завтра")  # бот остаётся на том же шаге
    assert "Время" in tg.send(1, "12.10.2026")
    assert "Описание" in tg.send(1, "18:00")
    assert "создано" in tg.send(1, "купить цветы")
    event = Event.objects.get(owner__telegram_id=1, name="ДР мамы")
    assert event.details == "купить цветы"
    assert "купить цветы" in tg.send(1, "/read_event ДР мамы")


def test_create_with_skip_and_cancel(tg):
    tg.register(1)
    tg.send(1, "/create_event")
    tg.send(1, "Черновик")
    assert "отменено" in tg.send(1, "/cancel")
    assert tg.send(1, "/events") == "Событий пока нет."
    assert "создано" in tg.create_event(1, "Встреча", "01.10.2026", "09:00")
    assert tg.send(1, "/events") == "📌 Встреча — 01.10.2026 в 09:00"


def test_edit_event(tg):
    tg.register(1)
    tg.create_event(1, "ДР", "12.10.2026", "18:00", "торт")
    tg.send(1, "/edit_event")
    assert "нет" in tg.send(1, "Нет такого")
    for text in ["ДР", "-", "19:30"]:
        tg.send(1, text)
    assert "обновлено" in tg.send(1, "два торта")
    assert tg.send(1, "/read_event ДР") == "📌 ДР — 12.10.2026 в 19:30\nдва торта"


def test_delete_event(tg):
    tg.register(1)
    tg.create_event(1, "ДР")
    assert "название" in tg.send(1, "/delete_event")
    assert "удалено" in tg.send(1, "ДР")
    assert not Event.objects.exists()


def test_users_are_isolated(tg):
    tg.register(1)
    tg.register(2)
    tg.create_event(1, "Секрет")
    assert "нет" in tg.send(2, "/read_event Секрет")
    assert "нет" in tg.send(2, "/delete_event Секрет")
    assert tg.send(2, "/events") == "Событий пока нет."
    assert Event.objects.filter(name="Секрет").count() == 1


def test_unknown_message(tg):
    assert "/help" in tg.send(1, "привет")
