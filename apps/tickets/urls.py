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
    path(
        "<int:number>/due-date/",
        views.ticket_change_due_date,
        name="change_due_date",
    ),
    path(
        "<int:number>/comments/add/",
        views.ticket_add_comment,
        name="add_comment",
    ),
    path(
        "<int:number>/attachments/upload/",
        views.ticket_upload_attachment,
        name="upload_attachment",
    ),
    path(
        "<int:number>/attachments/<int:attachment_id>/download/",
        views.ticket_download_attachment,
        name="download_attachment",
    ),
]
