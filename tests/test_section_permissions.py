import pytest

from django.contrib.auth.models import Group, Permission
from django.urls import reverse


@pytest.fixture
def employee(django_user_model):
    return django_user_model.objects.create_user(
        username="employee",
        password="TestPassword123!",
    )


@pytest.fixture
def forms_group(db):
    group, _ = Group.objects.get_or_create(
        name="forms_access",
    )

    permission = Permission.objects.get(
        content_type__app_label="forms",
        codename="access_forms",
    )

    group.permissions.add(permission)

    return group


@pytest.mark.django_db
def test_forms_denied_without_permission(client, employee):
    client.force_login(employee)

    response = client.get(reverse("forms"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_forms_allowed_with_group(
    client,
    employee,
    forms_group,
):
    employee.groups.add(forms_group)

    client.force_login(employee)

    response = client.get(reverse("forms"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_forms_hidden_from_navigation(client, employee):
    client.force_login(employee)

    response = client.get(reverse("home"))
    content = response.content.decode("utf-8")

    assert 'href="/forms/"' not in content


@pytest.mark.django_db
def test_forms_visible_in_navigation(
    client,
    employee,
    forms_group,
):
    employee.groups.add(forms_group)

    client.force_login(employee)

    response = client.get(reverse("home"))
    content = response.content.decode("utf-8")

    assert 'href="/forms/"' in content


@pytest.mark.django_db
def test_public_sections_available_to_employee(client, employee):
    client.force_login(employee)

    for url_name in [
        "home",
        "tickets:list",
        "contacts",
        "access",
        "profile",
    ]:
        response = client.get(reverse(url_name))
        assert response.status_code == 200