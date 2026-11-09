from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .selectors import get_visible_tickets


@login_required
def ticket_list(request):
    tickets = get_visible_tickets(request.user).order_by(
        "-created_at",
        "-number",
    )

    paginator = Paginator(tickets, 20)
    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "tickets/ticket_list.html",
        {
            "page_obj": page_obj,
            "tickets": page_obj.object_list,
        },
    )