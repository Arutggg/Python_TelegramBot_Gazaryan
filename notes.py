"""Функции для работы с заметками.

Функции не используют input() и print(): принимают данные аргументами
и возвращают текст ответа, поэтому их можно вызывать из обработчиков бота.
"""
import os
import re

NOTES_DIR = "notes"
FORBIDDEN_SYMBOLS = re.compile(r'[\\|/*<>?:"]')


def _note_path(note_name):
    return os.path.join(NOTES_DIR, f"{note_name}.txt")


def _list_notes():
    """Возвращает список (название, текст) всех заметок."""
    if not os.path.isdir(NOTES_DIR):
        return []
    notes = []
    for file_name in os.listdir(NOTES_DIR):
        if file_name.endswith(".txt"):
            with open(os.path.join(NOTES_DIR, file_name), encoding="utf-8") as file:
                notes.append((file_name[:-4], file.read()))
    return notes


def create_note(note_name, note_text):
    if not note_name:
        return "Название заметки не может быть пустым."
    if FORBIDDEN_SYMBOLS.search(note_name):
        return "В названии есть недопустимые символы. Переименуйте заметку."
    os.makedirs(NOTES_DIR, exist_ok=True)
    existed = os.path.isfile(_note_path(note_name))
    with open(_note_path(note_name), "w", encoding="utf-8") as file:
        file.write(note_text)
    return f"Заметка «{note_name}» {'перезаписана' if existed else 'создана'}."


def read_note(note_name):
    if not os.path.isfile(_note_path(note_name)):
        return "Такой заметки не существует."
    with open(_note_path(note_name), encoding="utf-8") as file:
        return f"Заметка «{note_name}»:\n{file.read()}"


def edit_note(note_name, new_text):
    if not os.path.isfile(_note_path(note_name)):
        return "Такой заметки не существует."
    with open(_note_path(note_name), "w", encoding="utf-8") as file:
        file.write(new_text)
    return f"Заметка «{note_name}» обновлена."


def delete_note(note_name):
    if not os.path.isfile(_note_path(note_name)):
        return "Такой заметки не существует."
    os.remove(_note_path(note_name))
    return f"Заметка «{note_name}» удалена."


def _format_notes(notes, title):
    if not notes:
        return "Заметок пока нет."
    lines = [f"{i}. {name} ({len(text)} симв.)" for i, (name, text) in enumerate(notes, 1)]
    return title + "\n" + "\n".join(lines)


def display_notes():
    """Все заметки от самой короткой до самой длинной."""
    notes = sorted(_list_notes(), key=lambda note: len(note[1]))
    return _format_notes(notes, "Заметки от самой короткой до самой длинной:")


def display_sorted_notes():
    """Все заметки от самой длинной до самой короткой."""
    notes = sorted(_list_notes(), key=lambda note: len(note[1]), reverse=True)
    return _format_notes(notes, "Заметки от самой длинной до самой короткой:")
