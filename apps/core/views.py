from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def section_placeholder(request, section_name):
    sections = {
        "forms": "Формы",
        "contacts": "Контакты",
        "access": "Доступ",
    }

    title = sections.get(section_name)

    if title is None:
        from django.http import Http404
        raise Http404

    return render(
        request,
        "core/placeholder.html",
        {"section_title": title},
    )
