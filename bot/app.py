import functools
import io
import logging
import urllib.request

from django.conf import settings
from django.db import close_old_connections, connection
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    TypeHandler,
    Updater,
)

from calendar_app.meetings import (
    DEFAULT_DURATION,
    create_meeting,
    find_user,
    respond_to_meeting,
    user_meetings,
)
from calendar_app.models import MeetingStatus
from calendar_app.tokens import make_token
from calendar_app.services import (
    DATE_FORMAT,
    TIME_FORMAT,
    Calendar,
    CalendarError,
    get_user,
    parse_date,
    parse_time,
    public_events,
    register_user,
)

logger = logging.getLogger(__name__)

# Состояния диалогов: бот помнит, на каком шаге находится пользователь
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
TEXT = Filters.text & ~Filters.command

HELP_TEXT = (
    "Команды:\n"
    "/register — зарегистрироваться\n"
    "/login — подключить Telegram ID к учётной записи и получить ссылку на личный кабинет\n"
    "/calendar — мой календарь: события и встречи\n"
    "/create_event — создать событие\n"
    "/events — все мои события\n"
    "/read_event [название] — показать событие\n"
    "/edit_event — изменить событие\n"
    "/delete_event [название] — удалить событие\n"
    "/share [название] — поделиться событием (без названия — выбрать кнопками)\n"
    "/unshare название — скрыть событие\n"
    "/shared [@username] — общие события других пользователей\n"
    "/export — выгрузить мои события в CSV или JSON\n"
    "/meeting — назначить встречу другим пользователям\n"
    "/meetings — мои встречи и их статусы\n"
    "/cancel — отменить текущее действие"
)


def format_event(event, with_owner=False):
    icon = "🌐" if event.is_public else "📌"
    owner = f" ({event.owner})" if with_owner else ""
    text = f"{icon} {event.name}{owner} — {event.date.strftime(DATE_FORMAT)} в {event.time.strftime(TIME_FORMAT)}"
    if event.details:
        text += f"\n{event.details}"
    return text


def format_events(events, empty_text="Событий пока нет.", with_owner=False):
    if not events:
        return empty_text
    return "\n\n".join(format_event(event, with_owner) for event in events)


STATUS_ICONS = {
    MeetingStatus.PENDING: "⏳",
    MeetingStatus.CONFIRMED: "✅",
    MeetingStatus.CANCELLED: "❌",
}


def format_meeting(meeting):
    participants = ", ".join(
        f"{invitation.user} {STATUS_ICONS[invitation.status]}"
        for invitation in meeting.invitations.all()
    )
    return (
        f"{STATUS_ICONS[meeting.status]} {meeting.title} — "
        f"{meeting.date.strftime(DATE_FORMAT)} в {meeting.time.strftime(TIME_FORMAT)} "
        f"({meeting.duration_minutes} мин)\n"
        f"Статус: {meeting.get_status_display()}\n"
        f"Организатор: {meeting.organizer}\n"
        f"Участники: {participants}"
    )


def registered_only(handler):
    """Пускает к команде только зарегистрированных и передаёт в обработчик его календарь."""

    @functools.wraps(handler)
    def wrapper(update, context):
        user = get_user(update.effective_user.id)
        if user is None:
            update.message.reply_text("Сначала зарегистрируйтесь: /register")
            return ConversationHandler.END
        return handler(update, context, Calendar(user))

    return wrapper


# ---------- Общие команды ----------

def start(update, context):
    update.message.reply_text("Привет! Я бот-календарь.\n\n" + HELP_TEXT)


def register(update, context):
    tg_user = update.effective_user
    _, created = register_user(tg_user.id, tg_user.username, tg_user.first_name)
    if created:
        update.message.reply_text(
            f"Готово, {tg_user.first_name}! Теперь можно создать событие: /create_event"
        )
    else:
        update.message.reply_text("Вы уже зарегистрированы.")


def cabinet_url(user):
    return f"{settings.WEB_URL}/cabinet/{make_token(user)}/"


def login(update, context):
    """Подключает Telegram ID к учётной записи (создаёт её при необходимости)
    и присылает ссылку на личный кабинет. ID берём из сообщения, а не из текста:
    так нельзя войти под чужим ID."""
    tg_user = update.effective_user
    user, created = register_user(tg_user.id, tg_user.username, tg_user.first_name)
    update.message.reply_text(
        f"{'Учётная запись создана' if created else 'Вы вошли'}.\n"
        f"Ваш Telegram ID: {user.telegram_id}\n\n"
        f"Личный кабинет (ссылка действует неделю):\n{cabinet_url(user)}"
    )


@registered_only
def show_calendar(update, context, calendar):
    meetings = user_meetings(calendar.user)
    text = "🗓 Ваш календарь\n\nСобытия:\n\n" + format_events(calendar.display_events())
    text += "\n\nВстречи:\n\n" + (
        "\n\n".join(format_meeting(meeting) for meeting in meetings) if meetings else "Встреч пока нет."
    )
    shared = public_events(exclude_user=calendar.user)
    text += "\n\nОбщие события:\n\n" + format_events(
        shared, "Другие пользователи пока ничем не поделились.", with_owner=True
    )
    update.message.reply_text(text)


@registered_only
def display_events(update, context, calendar):
    update.message.reply_text(format_events(calendar.display_events()))


def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def unknown(update, context):
    update.message.reply_text("Не понимаю. Список команд — /help")


# ---------- Создание события: название → дата → время → описание ----------

@registered_only
def create_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Как назовём событие?")
    return CREATE_NAME


@registered_only
def create_name(update, context, calendar):
    name = update.message.text.strip()
    if calendar.event_exists(name):
        update.message.reply_text("Событие с таким названием уже есть. Введите другое:")
        return CREATE_NAME
    context.user_data["name"] = name
    update.message.reply_text("Дата события (ДД.ММ.ГГГГ):")
    return CREATE_DATE


def create_date(update, context):
    try:
        parse_date(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return CREATE_DATE
    context.user_data["date"] = update.message.text.strip()
    update.message.reply_text("Время события (ЧЧ:ММ):")
    return CREATE_TIME


def create_time(update, context):
    try:
        parse_time(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return CREATE_TIME
    context.user_data["time"] = update.message.text.strip()
    update.message.reply_text("Описание события (или /skip, чтобы пропустить):")
    return CREATE_DETAILS


@registered_only
def create_details(update, context, calendar):
    details = "" if update.message.text == "/skip" else update.message.text.strip()
    data = context.user_data
    try:
        calendar.create_event(data["name"], data["date"], data["time"], details)
        update.message.reply_text(f"Событие «{data['name']}» создано.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    data.clear()
    return ConversationHandler.END


# ---------- Редактирование: название → дата → время → описание («-» = без изменений) ----------

@registered_only
def edit_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Какое событие изменить? Введите название:")
    return EDIT_NAME


@registered_only
def edit_name(update, context, calendar):
    name = update.message.text.strip()
    if not calendar.event_exists(name):
        update.message.reply_text("Такого события нет. Введите название ещё раз или /cancel:")
        return EDIT_NAME
    context.user_data["name"] = name
    update.message.reply_text(f"Новая дата (ДД.ММ.ГГГГ) или «{KEEP}», чтобы оставить:")
    return EDIT_DATE


def edit_date(update, context):
    text = update.message.text.strip()
    if text != KEEP:
        try:
            parse_date(text)
        except CalendarError as error:
            update.message.reply_text(str(error))
            return EDIT_DATE
        context.user_data["date"] = text
    update.message.reply_text(f"Новое время (ЧЧ:ММ) или «{KEEP}»:")
    return EDIT_TIME


def edit_time(update, context):
    text = update.message.text.strip()
    if text != KEEP:
        try:
            parse_time(text)
        except CalendarError as error:
            update.message.reply_text(str(error))
            return EDIT_TIME
        context.user_data["time"] = text
    update.message.reply_text(f"Новое описание или «{KEEP}»:")
    return EDIT_DETAILS


@registered_only
def edit_details(update, context, calendar):
    text = update.message.text.strip()
    data = context.user_data
    try:
        calendar.edit_event(
            data["name"],
            new_date=data.get("date"),
            new_description=None if text == KEEP else text,
            new_time=data.get("time"),
        )
        update.message.reply_text(f"Событие «{data['name']}» обновлено.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    data.clear()
    return ConversationHandler.END


# ---------- Просмотр и удаление: название можно передать сразу или ввести следующим сообщением ----------

def run_action(update, calendar, action, name):
    try:
        if action == "read":
            update.message.reply_text(format_event(calendar.read_event(name)))
        else:
            calendar.delete_event(name)
            update.message.reply_text(f"Событие «{name}» удалено.")
    except CalendarError as error:
        update.message.reply_text(str(error))
    return ConversationHandler.END


def action_start(action):
    @registered_only
    def handler(update, context, calendar):
        name = " ".join(context.args).strip()
        if name:
            return run_action(update, calendar, action, name)
        context.user_data["action"] = action
        update.message.reply_text("Введите название события:")
        return ASK_NAME

    return handler


@registered_only
def ask_name(update, context, calendar):
    action = context.user_data.pop("action")
    return run_action(update, calendar, action, update.message.text.strip())


# ---------- Встречи: тема → дата → время → длительность → участники ----------

@registered_only
def meeting_start(update, context, calendar):
    context.user_data.clear()
    update.message.reply_text("Тема встречи?")
    return MEETING_TITLE


def meeting_title(update, context):
    context.user_data["title"] = update.message.text.strip()
    update.message.reply_text("Дата встречи (ДД.ММ.ГГГГ):")
    return MEETING_DATE


def meeting_date(update, context):
    try:
        parse_date(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return MEETING_DATE
    context.user_data["date"] = update.message.text.strip()
    update.message.reply_text("Время начала (ЧЧ:ММ):")
    return MEETING_TIME


def meeting_time(update, context):
    try:
        parse_time(update.message.text)
    except CalendarError as error:
        update.message.reply_text(str(error))
        return MEETING_TIME
    context.user_data["time"] = update.message.text.strip()
    update.message.reply_text(
        f"Длительность в минутах (или /skip — {DEFAULT_DURATION} минут):"
    )
    return MEETING_DURATION


def meeting_duration(update, context):
    text = update.message.text.strip()
    if text == "/skip":
        duration = DEFAULT_DURATION
    elif text.isdigit() and int(text) > 0:
        duration = int(text)
    else:
        update.message.reply_text("Введите число минут, например 30:")
        return MEETING_DURATION
    context.user_data["duration"] = duration
    update.message.reply_text(
        "Кого пригласить? Напишите @username или Telegram ID через пробел.\n"
        "Участники должны быть зарегистрированы в боте."
    )
    return MEETING_PARTICIPANTS


def invitation_keyboard(meeting):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Принять", callback_data=f"meeting:accept:{meeting.id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"meeting:decline:{meeting.id}"),
    ]])


@registered_only
def meeting_participants(update, context, calendar):
    data = context.user_data
    identifiers = update.message.text.replace(",", " ").split()
    try:
        meeting, invited, problems = create_meeting(
            calendar.user, data["title"], data["date"], data["time"], data["duration"], identifiers
        )
    except CalendarError as error:
        update.message.reply_text(f"{error}\n\nВведите других участников или /cancel:")
        return MEETING_PARTICIPANTS
    data.clear()

    for user in invited:
        context.bot.send_message(
            chat_id=user.telegram_id,
            text=f"{calendar.user} приглашает вас на встречу:\n\n{format_meeting(meeting)}",
            reply_markup=invitation_keyboard(meeting),
        )
    text = "Встреча создана, приглашения отправлены:\n\n" + format_meeting(meeting)
    if problems:
        text += "\n\nНе приглашены:\n" + "\n".join(problems)
    update.message.reply_text(text)
    return ConversationHandler.END


@registered_only
def list_meetings(update, context, calendar):
    meetings = user_meetings(calendar.user)
    if not meetings:
        update.message.reply_text("Встреч пока нет. Назначить: /meeting")
        return
    update.message.reply_text(
        "Ваши встречи:\n\n" + "\n\n".join(format_meeting(meeting) for meeting in meetings)
    )


def answer_invitation(update, context):
    """Нажатие «Принять» / «Отклонить» под приглашением."""
    query = update.callback_query
    _, action, meeting_id = query.data.split(":")
    user = get_user(query.from_user.id)
    try:
        meeting = respond_to_meeting(int(meeting_id), user, accept=action == "accept")
    except CalendarError as error:
        query.answer(str(error), show_alert=True)
        return
    query.answer()
    accepted = action == "accept"
    query.edit_message_text(
        f"Вы {'приняли' if accepted else 'отклонили'} приглашение.\n\n{format_meeting(meeting)}"
    )
    context.bot.send_message(
        chat_id=meeting.organizer.telegram_id,
        text=f"{user} {'принял(а)' if accepted else 'отклонил(а)'} приглашение.\n\n"
        f"{format_meeting(meeting)}",
    )


# ---------- Публичные события ----------

def share_keyboard(events):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'🌐' if event.is_public else '🔒'} {event.name}",
            callback_data=f"share:{event.id}",
        )]
        for event in events
    ])


@registered_only
def share(update, context, calendar):
    name = " ".join(context.args).strip()
    if name:
        try:
            calendar.set_public(name, True)
            update.message.reply_text(f"Событие «{name}» теперь видят другие пользователи.")
        except CalendarError as error:
            update.message.reply_text(str(error))
        return
    events = calendar.display_events()
    if not events:
        update.message.reply_text("Событий пока нет.")
        return
    update.message.reply_text(
        "Нажмите на событие, чтобы открыть или скрыть его.\n🌐 — видят все, 🔒 — только вы.",
        reply_markup=share_keyboard(events),
    )


@registered_only
def unshare(update, context, calendar):
    name = " ".join(context.args).strip()
    if not name:
        update.message.reply_text("Формат: /unshare название")
        return
    try:
        calendar.set_public(name, False)
        update.message.reply_text(f"Событие «{name}» скрыто.")
    except CalendarError as error:
        update.message.reply_text(str(error))


def toggle_share(update, context):
    """Нажатие на событие в списке /share."""
    query = update.callback_query
    user = get_user(query.from_user.id)
    if user is None:
        query.answer("Сначала зарегистрируйтесь: /register", show_alert=True)
        return
    calendar = Calendar(user)
    try:
        event = calendar.toggle_public(int(query.data.split(":")[1]))
    except CalendarError as error:
        query.answer(str(error), show_alert=True)
        return
    query.answer("Теперь видят все" if event.is_public else "Скрыто")
    query.edit_message_reply_markup(reply_markup=share_keyboard(calendar.display_events()))


@registered_only
def shared(update, context, calendar):
    identifier = " ".join(context.args).strip()
    if identifier:
        owner = find_user(identifier)
        if owner is None:
            update.message.reply_text("Такой пользователь не зарегистрирован в боте.")
            return
        events = public_events(owner=owner)
        title = f"Общие события {owner}:"
    else:
        events = public_events(exclude_user=calendar.user)
        title = "Общие события других пользователей:"
    update.message.reply_text(
        f"{title}\n\n" + format_events(events, "Общих событий нет.", with_owner=not identifier)
    )


# ---------- Выгрузка событий ----------

def export_url(user, file_format):
    return f"{settings.WEB_URL}/export/{make_token(user)}/?format={file_format}"


def download_export(url):
    """Запрашивает выгрузку у веб-приложения и возвращает содержимое файла."""
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read()


@registered_only
def export(update, context, calendar):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📄 CSV", callback_data="export:csv"),
        InlineKeyboardButton("🧾 JSON", callback_data="export:json"),
    ]])
    update.message.reply_text(
        "В каком формате выгрузить события?\n\n"
        f"Или скачайте в браузере:\n{export_url(calendar.user, 'csv')}",
        reply_markup=keyboard,
    )


def send_export(update, context):
    """Нажатие на кнопку формата: бот скачивает файл с веб-приложения и присылает его."""
    query = update.callback_query
    user = get_user(query.from_user.id)
    if user is None:
        query.answer("Сначала зарегистрируйтесь: /register", show_alert=True)
        return
    file_format = query.data.split(":")[1]
    try:
        content = download_export(export_url(user, file_format))
    except OSError:
        logger.exception("Не удалось получить выгрузку")
        query.answer("Веб-приложение недоступно, попробуйте позже.", show_alert=True)
        return
    query.answer()
    context.bot.send_document(
        chat_id=user.telegram_id,
        document=io.BytesIO(content),
        filename=f"events.{file_format}",
        caption="Ваши события",
    )


def error_handler(update, context):
    logger.exception("Ошибка при обработке обновления", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text("Что-то пошло не так. Попробуйте ещё раз.")


def refresh_db_connection(update, context):
    """Бот работает долго: перед каждым апдейтом закрываем устаревшие соединения с БД."""
    if not connection.in_atomic_block:  # внутри транзакции (например, в тестах) не трогаем
        close_old_connections()


def create_updater(token=None):
    """Собирает бота и регистрирует обработчики."""
    updater = Updater(token=token or settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(TypeHandler(Update, refresh_db_connection), group=-1)

    cancel_handler = CommandHandler("cancel", cancel)

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("create_event", create_start)],
        states={
            CREATE_NAME: [MessageHandler(TEXT, create_name)],
            CREATE_DATE: [MessageHandler(TEXT, create_date)],
            CREATE_TIME: [MessageHandler(TEXT, create_time)],
            CREATE_DETAILS: [
                MessageHandler(TEXT, create_details),
                CommandHandler("skip", create_details),
            ],
        },
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("edit_event", edit_start)],
        states={
            EDIT_NAME: [MessageHandler(TEXT, edit_name)],
            EDIT_DATE: [MessageHandler(TEXT, edit_date)],
            EDIT_TIME: [MessageHandler(TEXT, edit_time)],
            EDIT_DETAILS: [MessageHandler(TEXT, edit_details)],
        },
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("read_event", action_start("read")),
            CommandHandler("delete_event", action_start("delete")),
        ],
        states={ASK_NAME: [MessageHandler(TEXT, ask_name)]},
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))

    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler("meeting", meeting_start)],
        states={
            MEETING_TITLE: [MessageHandler(TEXT, meeting_title)],
            MEETING_DATE: [MessageHandler(TEXT, meeting_date)],
            MEETING_TIME: [MessageHandler(TEXT, meeting_time)],
            MEETING_DURATION: [
                MessageHandler(TEXT, meeting_duration),
                CommandHandler("skip", meeting_duration),
            ],
            MEETING_PARTICIPANTS: [MessageHandler(TEXT, meeting_participants)],
        },
        fallbacks=[cancel_handler],
        allow_reentry=True,
    ))
    dispatcher.add_handler(CallbackQueryHandler(answer_invitation, pattern=r"^meeting:(accept|decline):\d+$"))

    dispatcher.add_handler(CommandHandler(["start", "help"], start))
    dispatcher.add_handler(CommandHandler("meetings", list_meetings))
    dispatcher.add_handler(CommandHandler("export", export))
    dispatcher.add_handler(CallbackQueryHandler(send_export, pattern=r"^export:(csv|json)$"))
    dispatcher.add_handler(CommandHandler("share", share))
    dispatcher.add_handler(CommandHandler("unshare", unshare))
    dispatcher.add_handler(CommandHandler("shared", shared))
    dispatcher.add_handler(CallbackQueryHandler(toggle_share, pattern=r"^share:\d+$"))
    dispatcher.add_handler(CommandHandler("register", register))
    dispatcher.add_handler(CommandHandler("login", login))
    dispatcher.add_handler(CommandHandler("calendar", show_calendar))
    dispatcher.add_handler(CommandHandler("events", display_events))
    dispatcher.add_handler(cancel_handler)
    dispatcher.add_handler(MessageHandler(Filters.all, unknown))
    dispatcher.add_error_handler(error_handler)
    return updater
