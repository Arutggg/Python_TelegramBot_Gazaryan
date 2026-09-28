from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("users", views.BotUserViewSet)
router.register("events", views.EventViewSet, basename="event")
router.register("meetings", views.MeetingViewSet)
router.register("statistics", views.BotStatisticsViewSet)
router.register("public-events", views.PublicEventViewSet, basename="public-event")

urlpatterns = router.urls
