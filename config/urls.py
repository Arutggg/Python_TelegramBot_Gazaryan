from django.contrib import admin
from django.urls import path

admin.site.site_header = "Бот-календарь: администрирование"

urlpatterns = [
    path("admin/", admin.site.urls),
]
