from django.urls import path
from . import views


app_name = "tickets"

urlpatterns = [
    path(
        "",
        views.ticket_list,
        name="list",
    ),
    path(
        "create/",
        views.ticket_create,
        name="create",
    ),
    path(
        "<int:number>/",
        views.ticket_detail,
        name="detail",
    ),
    path(
        "<int:number>/take/",
        views.ticket_take,
        name="take",
    ),
    path(
        "<int:number>/assign/",
        views.ticket_assign,
        name="assign",
    ),
    path(
        "<int:number>/complete/",
        views.ticket_complete,
        name="complete",
    ),
    path(
        "<int:number>/reject/",
        views.ticket_reject,
        name="reject",
    ),
]
