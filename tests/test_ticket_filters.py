import pytest

from django.urls import reverse

from apps.organization.models import Department
from apps.tickets.models import Ticket


@pytest.fixture
def users(django_user_model):
    author = django_user_model.objects.create_user(
        username="filter_author",
        password="TestPassword123!",
    )

    outsider = django_user_model.objects.create_user(
        username="filter_outsider",
        password="TestPassword123!",
    )

    return author, outsider


@pytest.fixture
def departments(db):
    it = Department.objects.create(
        name="ИТ",
        code="it",
    )

    one_c = Department.objects.create(
        name="1С",
        code="1c",
    )

    return it, one_c


@pytest.fixture
def tickets(users, departments):
    author, outsider = users
    it, one_c = departments

    printer = Ticket.objects.create(
        author=author,
        department=it,
        title="Не работает принтер",
        description="Описание",
        status=Ticket.Status.CREATED,
    )

    computer = Ticket.objects.create(
        author=author,
        department=it,
        title="Не включается компьютер",
        description="Описание",
        status=Ticket.Status.IN_PROGRESS,
    )

    foreign = Ticket.objects.create(
        author=outsider,
        department=one_c,
        title="Ошибка в 1С",
        description="Описание",
        status=Ticket.Status.CREATED,
    )

    return printer, computer, foreign


@pytest.mark.django_db
def test_search_by_title(client, users, tickets):
    author, _ = users
    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"q": "принтер"},
    )

    content = response.content.decode("utf-8")

    assert response.status_code == 200
    assert "Не работает принтер" in content
    assert "Не включается компьютер" not in content


@pytest.mark.django_db
def test_search_by_number(client, users, tickets):
    author, _ = users
    printer, _, _ = tickets

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"q": str(printer.number)},
    )

    assert response.status_code == 200

    result_tickets = list(response.context["tickets"])

    assert printer in result_tickets


@pytest.mark.django_db
def test_filter_by_status(client, users, tickets):
    author, _ = users
    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"status": Ticket.Status.IN_PROGRESS},
    )

    result_tickets = list(response.context["tickets"])

    assert tickets[1] in result_tickets
    assert tickets[0] not in result_tickets


@pytest.mark.django_db
def test_filter_by_department(
    client, users, departments, tickets
):
    author, _ = users
    it, _ = departments

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"department": it.pk},
    )

    result_tickets = list(response.context["tickets"])

    assert tickets[0] in result_tickets
    assert tickets[1] in result_tickets
    assert tickets[2] not in result_tickets


@pytest.mark.django_db
def test_filter_does_not_expose_foreign_ticket(
    client, users, tickets
):
    author, _ = users
    foreign = tickets[2]

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"q": "Ошибка в 1С"},
    )

    result_tickets = list(response.context["tickets"])

    assert foreign not in result_tickets
    assert response.context["total_count"] == 0


@pytest.mark.django_db
def test_foreign_department_not_in_filter(
    client, users, departments, tickets
):
    author, _ = users
    _, one_c = departments

    client.force_login(author)

    response = client.get(reverse("tickets:list"))

    form = response.context["filter_form"]

    assert one_c not in form.fields["department"].queryset


@pytest.mark.django_db
def test_invalid_status_does_not_crash(
    client, users, tickets
):
    author, _ = users
    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"status": "unknown_status"},
    )

    assert response.status_code == 200
    assert response.context["filter_form"].is_valid() is False


@pytest.mark.django_db
def test_pagination_preserves_filters(
    client, users, departments
):
    author, _ = users
    it, _ = departments

    for index in range(25):
        Ticket.objects.create(
            author=author,
            department=it,
            title=f"Принтер {index}",
            description="Описание",
        )

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"q": "Принтер", "page": "1"},
    )

    assert response.status_code == 200

    content = response.content.decode("utf-8")

    assert "q=Принтер" in content or "q=%D0%9F" in content
    assert "page=2" in content

@pytest.mark.django_db
def test_filter_by_assignee(
    client, users, departments, tickets
):
    author, outsider = users

    printer, computer, _ = tickets

    printer.assignee = outsider
    printer.save(update_fields=["assignee"])

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"assignee": outsider.pk},
    )

    result_tickets = list(response.context["tickets"])

    assert printer in result_tickets
    assert computer not in result_tickets


@pytest.mark.django_db
def test_cannot_filter_by_foreign_department(
    client, users, departments, tickets
):
    author, _ = users
    _, one_c = departments

    client.force_login(author)

    response = client.get(
        reverse("tickets:list"),
        {"department": one_c.pk},
    )

    assert response.status_code == 200
    assert response.context["filter_form"].is_valid() is False


@pytest.mark.django_db
def test_foreign_assignee_not_in_filter(
    client, users, departments, tickets
):
    author, outsider = users
    _, _, foreign = tickets

    foreign.assignee = outsider
    foreign.save(update_fields=["assignee"])

    client.force_login(author)

    response = client.get(reverse("tickets:list"))

    form = response.context["filter_form"]

    assert outsider not in form.fields["assignee"].queryset

