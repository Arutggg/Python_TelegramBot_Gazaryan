import datetime
import json
import os

DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"


def parse_date(text):
    return datetime.datetime.strptime(text.strip(), DATE_FORMAT).date()


def parse_time(text):
    return datetime.datetime.strptime(text.strip(), TIME_FORMAT).time()


class Calendar:
    """Календарь событий. События хранятся в списке и сохраняются в JSON-файл."""

    def __init__(self, file_path="events.json"):
        self.file_path = file_path
        self.events = []
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as file:
                self.events = json.load(file)

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.events, file, ensure_ascii=False, indent=2)

    def _find(self, event_name):
        for event in self.events:
            if event["name"] == event_name:
                return event
        return None

    @staticmethod
    def _format(event):
        text = f"📌 {event['name']} — {event['date']} в {event['time']}"
        if event["details"]:
            text += f"\n{event['details']}"
        return text

    def create_event(self, event_name, event_date, event_time, event_details=""):
        try:
            date = parse_date(event_date).strftime(DATE_FORMAT)
            time = parse_time(event_time).strftime(TIME_FORMAT)
        except ValueError:
            return "Неверная дата или время. Формат: ДД.ММ.ГГГГ и ЧЧ:ММ."
        if self._find(event_name):
            return f"Событие «{event_name}» уже есть."
        self.events.append(
            {"name": event_name, "date": date, "time": time, "details": event_details}
        )
        self._save()
        return f"Событие «{event_name}» создано."

    def read_event(self, event_name):
        event = self._find(event_name)
        return self._format(event) if event else "Такого события нет."

    def edit_event(self, event_name, new_date=None, new_description=None, new_time=None):
        event = self._find(event_name)
        if not event:
            return "Такого события нет."
        try:
            if new_date:
                event["date"] = parse_date(new_date).strftime(DATE_FORMAT)
            if new_time:
                event["time"] = parse_time(new_time).strftime(TIME_FORMAT)
        except ValueError:
            return "Неверная дата или время. Формат: ДД.ММ.ГГГГ и ЧЧ:ММ."
        if new_description is not None:
            event["details"] = new_description
        self._save()
        return f"Событие «{event_name}» обновлено."

    def delete_event(self, event_name):
        event = self._find(event_name)
        if not event:
            return "Такого события нет."
        self.events.remove(event)
        self._save()
        return f"Событие «{event_name}» удалено."

    def display_events(self):
        if not self.events:
            return "Событий пока нет."
        events = sorted(
            self.events,
            key=lambda e: (parse_date(e["date"]), parse_time(e["time"])),
        )
        return "Ваши события:\n\n" + "\n\n".join(self._format(e) for e in events)
