from django.shortcuts import render


def ticket_list(request):
    return render(request, "tickets/list.html")
