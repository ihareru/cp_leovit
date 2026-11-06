import pytest
from django.urls import reverse


@pytest.fixture
def authenticated_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="testemployee",
        password="TestPassword123!",
    )

    client.force_login(user)

    return client


@pytest.mark.django_db
def test_home_page_requires_login(client):
    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_home_page_authenticated(authenticated_client):
    response = authenticated_client.get(reverse("home"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_tickets_page_requires_login(client):
    response = client.get(reverse("tickets:list"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_tickets_page_authenticated(authenticated_client):
    response = authenticated_client.get(reverse("tickets:list"))

    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["forms", "contacts", "access"],
)
def test_placeholder_pages_require_login(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["forms", "contacts", "access"],
)
def test_placeholder_pages_authenticated(
    authenticated_client,
    url_name,
):
    response = authenticated_client.get(reverse(url_name))

    assert response.status_code == 200
