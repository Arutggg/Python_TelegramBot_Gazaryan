"""Состояния диалогов: по ним бот помнит, на каком шаге находится пользователь."""
(
    CREATE_NAME,
    CREATE_DATE,
    CREATE_TIME,
    CREATE_DETAILS,
    EDIT_NAME,
    EDIT_DATE,
    EDIT_TIME,
    EDIT_DETAILS,
    ASK_NAME,
    MEETING_TITLE,
    MEETING_DATE,
    MEETING_TIME,
    MEETING_DURATION,
    MEETING_PARTICIPANTS,
) = range(14)

KEEP = "-"  # ввод «-» при редактировании оставляет старое значение
SKIP = "/skip"  # пропуск необязательного шага
