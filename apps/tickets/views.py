from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from .forms import TicketCreateForm
from .models import Ticket
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

@login_required
def ticket_create(request):

    if request.method == "POST":
        form = TicketCreateForm(request.POST)

        if form.is_valid():
            ticket = form.save(commit=False)

            ticket.author = request.user
            ticket.status = Ticket.Status.CREATED
            ticket.assignee = None

            ticket.save()

            messages.success(
                request,
                f"Заявка №{ticket.number} успешно создана."
            )

            return redirect("tickets:list")

    else:
        form = TicketCreateForm()

    return render(
        request,
        "tickets/ticket_create.html",
        {"form": form},
    )
