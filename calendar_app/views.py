from django.http import Http404
from django.shortcuts import render

from .meetings import user_meetings
from .tokens import user_from_token


def get_user_or_404(token):
    user = user_from_token(token)
    if user is None:
        raise Http404("Ссылка недействительна или устарела. Получите новую командой /login в боте.")
    return user


def cabinet(request, token):
    """Личный кабинет: календарь пользователя."""
    user = get_user_or_404(token)
    return render(request, "calendar_app/cabinet.html", {
        "profile": user,
        "events": user.events.all(),
        "meetings": user_meetings(user),
        "token": token,
    })
