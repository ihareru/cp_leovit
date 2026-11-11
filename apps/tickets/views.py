from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import (
    HttpResponseNotAllowed,
    FileResponse,
    Http404,
    QueryDict
)
from django.db import transaction
from .timeline import get_ticket_timeline
from .assignment_forms import TicketAssignForm
from .permissions import (
    can_execute_department_tickets,
    can_manage_department_tickets,
    can_change_ticket_due_date,
    can_comment_ticket,
    can_upload_ticket_attachment,
)
from .services import (
    take_ticket,
    assign_ticket,
    complete_ticket,
    reject_ticket,
    change_ticket_due_date
)
from .status_forms import TicketCompleteForm, TicketRejectForm
from .due_date_forms import TicketDueDateForm
from .forms import TicketCreateForm
from .models import Ticket, TicketAttachment
from .selectors import (
    get_visible_tickets,
    get_visible_ticket_or_404,
    filter_tickets
)
from .filter_forms import TicketFilterForm

from .comment_forms import TicketCommentForm
from .comment_services import add_ticket_comment

from .attachment_forms import TicketAttachmentForm
from .attachment_services import (
    add_ticket_attachment,
    add_ticket_attachments,
)


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

        attachment_form = TicketAttachmentForm(
            request.POST,
            request.FILES,
        )

        form_valid = form.is_valid()
        files_valid = attachment_form.is_valid()

        if form_valid and files_valid:
            uploaded_files = (
                attachment_form.cleaned_data["all_files"]
            )

            created_attachments = []

            try:
                with transaction.atomic():
                    ticket = form.save(commit=False)
                    ticket.author = request.user
                    ticket.status = Ticket.Status.CREATED
                    ticket.assignee = None
                    ticket.save()

                    created_attachments = add_ticket_attachments(
                        ticket_id=ticket.pk,
                        actor=request.user,
                        uploaded_files=uploaded_files,
                    )

            except ValidationError as exc:
                messages.error(
                    request,
                    "; ".join(exc.messages),
                )

            except Exception:
                for attachment in created_attachments:
                    attachment.file.delete(save=False)
                raise

            else:
                messages.success(
                    request,
                    f"Заявка №{ticket.number} успешно создана.",
                )
                return redirect("tickets:list")

    else:
        form = TicketCreateForm()
        attachment_form = TicketAttachmentForm()

    return render(
        request,
        "tickets/ticket_create.html",
        {
            "form": form,
            "attachment_form": attachment_form,
        },
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

    timeline = get_ticket_timeline(ticket)

    comments = (
        ticket.comments
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("created_at", "pk")
    )

    can_comment = can_comment_ticket(
        request.user,
        ticket,
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

    attachments = (
        ticket.attachments
        .select_related("uploaded_by")
        .order_by("created_at", "pk")
    )

    can_upload_attachment = can_upload_ticket_attachment(
        request.user,
        ticket,
    )

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "can_take": can_take,
            "can_assign": can_assign,
            "assignment_form": assignment_form,
            "can_complete": can_complete,
            "can_reject": can_reject,
            "complete_form": TicketCompleteForm(),
            "reject_form": TicketRejectForm(),
            "can_change_due_date": can_change_due_date,
            "due_date_form": due_date_form,
            "timeline": timeline,
            "comments": comments,
            "can_comment": can_comment,
            "comment_form": TicketCommentForm(),
            "attachments": attachments,
            "can_upload_attachment": can_upload_attachment,
            "attachment_form": TicketAttachmentForm(),
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



@login_required
def ticket_add_comment(request, number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    if not can_comment_ticket(request.user, ticket):
        raise PermissionDenied(
            "Нет прав на комментирование заявки."
        )

    form = TicketCommentForm(
        request.POST,
        request.FILES,
    )

    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

        return redirect(
            "tickets:detail",
            number=number,
        )

    created_attachments = []

    try:
        with transaction.atomic():
            comment = add_ticket_comment(
                ticket_id=ticket.pk,
                actor=request.user,
                text=form.cleaned_data["text"],
            )

            created_attachments = add_ticket_attachments(
                ticket_id=ticket.pk,
                actor=request.user,
                uploaded_files=form.cleaned_data["files"],
                comment=comment,
            )

    except ValidationError as exc:
        messages.error(
            request,
            "; ".join(exc.messages),
        )

    except Exception:
        for attachment in created_attachments:
            attachment.file.delete(save=False)
        raise

    else:
        messages.success(
            request,
            "Комментарий добавлен.",
        )

    return redirect(
        "tickets:detail",
        number=number,
    )


@login_required
def ticket_upload_attachment(request, number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    if not can_upload_ticket_attachment(
        request.user,
        ticket,
    ):
        raise PermissionDenied(
            "Нет прав на загрузку вложений."
        )

    form = TicketAttachmentForm(
        request.POST,
        request.FILES,
    )

    # Сначала проверяем форму.
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

        return redirect(
            "tickets:detail",
            number=number,
        )

    uploaded_files = form.cleaned_data["all_files"]

    if not uploaded_files:
        messages.error(
            request,
            "Выберите хотя бы один файл.",
        )
        return redirect(
            "tickets:detail",
            number=number,
        )

    try:
        attachments = add_ticket_attachments(
            ticket_id=ticket.pk,
            actor=request.user,
            uploaded_files=uploaded_files,
        )

    except ValidationError as exc:
        messages.error(
            request,
            "; ".join(exc.messages),
        )

    else:
        messages.success(
            request,
            f"Прикреплено файлов: {len(attachments)}.",
        )

    return redirect(
        "tickets:detail",
        number=number,
    )


@login_required
def ticket_download_attachment(
    request,
    number,
    attachment_id,
):
    ticket = get_visible_ticket_or_404(
        request.user,
        number,
    )

    attachment = get_object_or_404(
        TicketAttachment,
        pk=attachment_id,
        ticket=ticket,
    )

    try:
        file_handle = attachment.file.open("rb")
    except FileNotFoundError:
        raise Http404("Файл не найден.")

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=attachment.original_name,
        content_type="application/octet-stream",
    )

    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"

    return response
