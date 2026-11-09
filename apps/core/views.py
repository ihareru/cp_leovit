from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render

from apps.forms.permissions import can_access_forms


def home(request):
    return render(request, "core/home.html")


def section_placeholder(request, section_name):
    sections = {
        "forms": "Формы",
        "contacts": "Контакты",
        "access": "Корпоративные ресурсы",
    }

    title = sections.get(section_name)

    if title is None:
        raise Http404

    if section_name == "forms":
        if not can_access_forms(request.user):
            raise PermissionDenied(
                "У вас нет доступа к разделу Формы."
            )

    return render(
        request,
        "core/placeholder.html",
        {"section_title": title},
    )
