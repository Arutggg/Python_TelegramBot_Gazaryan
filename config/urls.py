from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Бот-календарь: администрирование"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("calendar_app.api.urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("", include("calendar_app.urls")),
]
