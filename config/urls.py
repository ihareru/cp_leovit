from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "",
        core_views.home,
        name="home",
    ),
    path(
        "tickets/",
        include("apps.tickets.urls"),
    ),
    path(
        "forms/",
        core_views.section_placeholder,
        {"section_name": "forms"},
        name="forms",
    ),
    path(
        "contacts/",
        core_views.section_placeholder,
        {"section_name": "contacts"},
        name="contacts",
    ),
    path(
        "access/",
        core_views.section_placeholder,
        {"section_name": "access"},
        name="access",
    ),
    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),
]