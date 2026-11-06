from django.http import Http404
from django.shortcuts import render


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

    return render(
        request,
        "core/placeholder.html",
        {"section_title": title},
    )