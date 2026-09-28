"""Общие инструменты для обработчиков: проверка регистрации и шаги диалогов."""
import functools

from telegram.ext import CommandHandler, ConversationHandler, Filters

from calendar_app.services import Calendar, CalendarError, get_user

TEXT = Filters.text & ~Filters.command
NOT_REGISTERED = "Сначала зарегистрируйтесь: /register"


def registered_only(handler):
    """Пускает к команде только зарегистрированных и передаёт в обработчик календарь пользователя."""

    @functools.wraps(handler)
    def wrapper(update, context):
        user = get_user(update.effective_user.id)
        if user is None:
            update.message.reply_text(NOT_REGISTERED)
            return ConversationHandler.END
        return handler(update, context, Calendar(user))

    return wrapper


def registered_callback(handler):
    """То же для нажатий на инлайн-кнопки: незарегистрированному показываем всплывающее сообщение."""

    @functools.wraps(handler)
    def wrapper(update, context):
        user = get_user(update.callback_query.from_user.id)
        if user is None:
            update.callback_query.answer(NOT_REGISTERED, show_alert=True)
            return
        return handler(update, context, Calendar(user))

    return wrapper


def input_step(key, validate, state, next_state, next_prompt, skip=None):
    """Создаёт шаг диалога.

    Шаг проверяет ввод функцией validate (она бросает CalendarError), сохраняет текст
    в context.user_data[key] и задаёт следующий вопрос. При ошибке бот повторяет
    текущий шаг. Если пользователь ввёл skip, поле не сохраняется.
    """

    def handler(update, context):
        text = update.message.text.strip()
        if text != skip:
            try:
                validate(text)
            except CalendarError as error:
                update.message.reply_text(str(error))
                return state
            context.user_data[key] = text
        update.message.reply_text(next_prompt)
        return next_state

    return handler


def command_text(context):
    """Текст после команды: «/share Концерт» → «Концерт»."""
    return " ".join(context.args).strip()


def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def conversation(entry_points, states):
    """ConversationHandler с общими настройками: /cancel в любой момент и перезапуск командой."""
    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
