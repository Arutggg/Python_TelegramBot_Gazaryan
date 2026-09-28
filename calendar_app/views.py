from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from .export import FORMATS, export_events
from .meetings import user_meetings
from .services import public_events
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
        "shared_events": public_events(exclude_user=user),
        "token": token,
    })


def export(request, token):
    """Выгрузка событий владельца токена. ?format=csv (по умолчанию) или ?format=json."""
    user = get_user_or_404(token)
    file_format = request.GET.get("format", "csv")
    if file_format not in FORMATS:
        return HttpResponseBadRequest("Поддерживаются форматы: " + ", ".join(FORMATS))
    content, content_type = export_events(user.events.all(), file_format)
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="events.{file_format}"'
    return response
