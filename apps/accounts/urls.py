from django.contrib.auth.views import LogoutView
from django.urls import path

from .password_reset_views import (
    password_reset_confirm,
    password_reset_request,
)
from .views import PortalLoginView, profile


urlpatterns = [
    path(
        "login/",
        PortalLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path(
        "profile/",
        profile,
        name="profile",
    ),
    path(
        "password-reset/",
        password_reset_request,
        name="password_reset_request",
    ),
    path(
        "password-reset/confirm/",
        password_reset_confirm,
        name="password_reset_confirm",
    ),
]
