from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def ticket_list(request):
    return render(request, "tickets/list.html")