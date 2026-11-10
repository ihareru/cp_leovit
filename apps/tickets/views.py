from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.http import QueryDict

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from .assignment_forms import TicketAssignForm
from .permissions import (
    can_execute_department_tickets,
    can_manage_department_tickets,
)
from .services import (
    take_ticket,
    assign_ticket,
    complete_ticket,
    reject_ticket,
    change_ticket_due_date
)
from .permissions import can_change_ticket_due_date
from .status_forms import TicketCompleteForm, TicketRejectForm
from .due_date_forms import TicketDueDateForm
from .forms import TicketCreateForm
from .models import Ticket
from .selectors import (
    get_visible_tickets,
    get_visible_ticket_or_404,
    filter_tickets
)
from .filter_forms import TicketFilterForm


@login_required
def ticket_list(request):

    visible_tickets = get_visible_tickets(request.user)

    filter_form = TicketFilterForm(
        request.GET,
        visible_tickets=visible_tickets,
    )

    if filter_form.is_valid():
        tickets = filter_tickets(
            visible_tickets,
            filter_form.cleaned_data,
        )
    else:
        tickets = visible_tickets.none()

    tickets = tickets.order_by(
        "-created_at",
        "-number",
    )

    paginator = Paginator(tickets, 20)

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    query_params = request.GET.copy()
    query_params.pop("page", None)

    query_string = query_params.urlencode()

    return render(
        request,
        "tickets/ticket_list.html",
        {
            "filter_form": filter_form,
            "page_obj": page_obj,
            "tickets": page_obj.object_list,
            "query_string": query_string,
            "total_count": paginator.count,
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

@login_required
def ticket_detail(request, number):
    """
    Просмотр карточки заявки.
    """

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    due_date_history = (
        ticket.due_date_history
        .select_related("changed_by")
        .order_by("-changed_at")
    )

    can_take = (
        ticket.status == Ticket.Status.CREATED
        and ticket.assignee_id is None
        and can_execute_department_tickets(
            request.user,
            ticket.department,
        )
    )

    can_assign = (
        ticket.status in (
            Ticket.Status.CREATED,
            Ticket.Status.IN_PROGRESS,
        )
        and can_manage_department_tickets(
            request.user,
            ticket.department,
        )
    )

    assignment_form = (
        TicketAssignForm(department=ticket.department)
        if can_assign
        else None
    )

    can_complete = (
            ticket.status == Ticket.Status.IN_PROGRESS
            and ticket.assignee_id is not None
            and (
                    (
                            ticket.assignee_id == request.user.pk
                            and can_execute_department_tickets(
                        request.user,
                        ticket.department,
                    )
                    )
                    or can_manage_department_tickets(
                request.user,
                ticket.department,
            )
            )
    )

    can_reject = (
        ticket.status in (
            Ticket.Status.CREATED,
            Ticket.Status.IN_PROGRESS,
        )
        and can_manage_department_tickets(
            request.user, ticket.department
        )
    )

    action_history = (
        ticket.action_history
        .select_related(
            "actor",
            "old_assignee",
            "new_assignee",
        )
    )

    can_change_due_date = can_change_ticket_due_date(
        request.user,
        ticket,
    )

    due_date_form = (
        TicketDueDateForm(
            initial={
                "new_due_date": ticket.due_date,
            }
        )
        if can_change_due_date
        else None
    )

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "due_date_history": due_date_history,
            "can_take": can_take,
            "can_assign": can_assign,
            "assignment_form": assignment_form,
            "can_complete": can_complete,
            "can_reject": can_reject,
            "complete_form": TicketCompleteForm(),
            "reject_form": TicketRejectForm(),
            "action_history": action_history,
            "can_change_due_date": can_change_due_date,
            "due_date_form": due_date_form,
        },
    )

@login_required
def ticket_take(request, number):

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    try:
        take_ticket(
            ticket_id=ticket.pk,
            actor=request.user,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(
            request,
            f"Заявка №{ticket.number} принята в работу.",
        )

    return redirect(
        "tickets:detail",
        number=ticket.number,
    )

@login_required
def ticket_assign(request, number):

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    if not can_manage_department_tickets(
        request.user,
        ticket.department,
    ):
        raise PermissionDenied

    form = TicketAssignForm(
        request.POST,
        department=ticket.department,
    )

    if not form.is_valid():
        messages.error(
            request,
            "Выберите действующего исполнителя отдела.",
        )
        return redirect(
            "tickets:detail",
            number=ticket.number,
        )

    try:
        assign_ticket(
            ticket_id=ticket.pk,
            assignee=form.cleaned_data["assignee"],
            actor=request.user,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(
            request,
            f"Исполнитель заявки №{ticket.number} назначен.",
        )

    return redirect(
        "tickets:detail",
        number=ticket.number,
    )


@login_required
def ticket_complete(request, number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user, number
    )

    form = TicketCompleteForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Некорректные данные.")
    else:
        try:
            complete_ticket(
                ticket_id=ticket.pk,
                actor=request.user,
                comment=form.cleaned_data["comment"],
            )
        except ValidationError as exc:
            messages.error(
                request, "; ".join(exc.messages)
            )
        else:
            messages.success(
                request, "Заявка исполнена."
            )

    return redirect("tickets:detail", number=number)


@login_required
def ticket_reject(request, number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user, number
    )

    if not can_manage_department_tickets(
        request.user, ticket.department
    ):
        raise PermissionDenied

    form = TicketRejectForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Необходимо указать причину отклонения.",
        )
    else:
        try:
            reject_ticket(
                ticket_id=ticket.pk,
                actor=request.user,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as exc:
            messages.error(
                request, "; ".join(exc.messages)
            )
        else:
            messages.success(
                request, "Заявка отклонена."
            )

    return redirect("tickets:detail", number=number)


@login_required
def ticket_change_due_date(request, number):
    """
    Изменение срока выполнения заявки.
    """

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    if not can_change_ticket_due_date(
            request.user,
            ticket,
    ):
        raise PermissionDenied(
            "Нет прав на изменение срока заявки."
        )

    form = TicketDueDateForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Проверьте новый срок и укажите причину изменения.",
        )

        return redirect(
            "tickets:detail",
            number=number,
        )

    try:
        change_ticket_due_date(
            ticket=ticket,
            new_due_date=form.cleaned_data["new_due_date"],
            changed_by=request.user,
            reason=form.cleaned_data["reason"],
        )

    except ValidationError as exc:
        messages.error(
            request,
            "; ".join(exc.messages),
        )

    else:
        messages.success(
            request,
            "Срок выполнения заявки обновлён.",
        )

    return redirect(
        "tickets:detail",
        number=number,
    )
