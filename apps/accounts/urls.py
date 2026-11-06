from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import PortalLoginView, profile


urlpatterns = [
    path(
        "login/",
        PortalLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(
            next_page="login",
        ),
        name="logout",
    ),
    path(
        "profile/",
        profile,
        name="profile",
    ),
]
