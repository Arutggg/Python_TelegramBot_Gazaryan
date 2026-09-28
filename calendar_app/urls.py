from django.urls import path

from . import views

app_name = "calendar_app"

urlpatterns = [
    path("cabinet/<str:token>/", views.cabinet, name="cabinet"),
]
