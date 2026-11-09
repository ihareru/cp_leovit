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
]
