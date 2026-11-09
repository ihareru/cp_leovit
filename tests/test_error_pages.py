import pytest

from django.core.exceptions import PermissionDenied
from django.test import override_settings


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_custom_404_page(client, django_user_model):

    user = django_user_model.objects.create_user(
        username="error_page_user",
        password="TestPassword123!",
    )

    client.force_login(user)

    response = client.get(
        "/page-that-does-not-exist/"
    )

    assert response.status_code == 404

    content = response.content.decode("utf-8")

    assert "Страница не найдена" in content
    assert "На главную" in content


import pytest

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, override_settings

from apps.core.error_views import permission_denied


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_custom_403_page(django_user_model):

    user = django_user_model.objects.create_user(
        username="error_403_user",
        password="TestPassword123!",
    )

    factory = RequestFactory()

    request = factory.get("/forbidden/")
    request.user = user

    response = permission_denied(
        request,
        PermissionDenied(),
    )

    assert response.status_code == 403

    content = response.content.decode("utf-8")

    assert "Доступ запрещён" in content
    assert "На главную" in content


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_foreign_ticket_404_page(client, django_user_model):
    from django.urls import reverse
    from apps.organization.models import Department
    from apps.tickets.models import Ticket

    author = django_user_model.objects.create_user(
        username="error_author",
        password="TestPassword123!",
    )

    outsider = django_user_model.objects.create_user(
        username="error_outsider",
        password="TestPassword123!",
    )

    department = Department.objects.create(
        name="Тестовый отдел ошибок",
        code="error-dept",
    )

    ticket = Ticket.objects.create(
        author=author,
        department=department,
        title="Закрытая заявка",
        description="Описание",
    )

    client.force_login(outsider)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 404
    assert "Страница не найдена" in response.content.decode("utf-8")
    assert "Закрытая заявка" not in response.content.decode("utf-8")
