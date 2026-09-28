"""Выгрузка событий пользователя в CSV и JSON."""
import csv
import io
import json

from .services import DATE_FORMAT, TIME_FORMAT

FORMATS = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json; charset=utf-8",
}
FIELDS = ["name", "date", "time", "details", "is_public"]


def event_rows(events):
    return [
        {
            "name": event.name,
            "date": event.date.strftime(DATE_FORMAT),
            "time": event.time.strftime(TIME_FORMAT),
            "details": event.details,
            "is_public": event.is_public,
        }
        for event in events
    ]


def to_csv(events):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(event_rows(events))
    # BOM, чтобы Excel правильно открыл кириллицу
    return "﻿" + buffer.getvalue()


def to_json(events):
    return json.dumps(event_rows(events), ensure_ascii=False, indent=2)


def export_events(events, file_format):
    """Возвращает (содержимое файла, content-type)."""
    if file_format not in FORMATS:
        raise ValueError(f"Неизвестный формат: {file_format}")
    content = to_csv(events) if file_format == "csv" else to_json(events)
    return content, FORMATS[file_format]
