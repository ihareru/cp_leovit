import pytest
from django.urls import reverse


@pytest.fixture
def portal_user(django_user_model):
    return django_user_model.objects.create_user(
        username="testemployee",
        password="TestPassword123!",
        first_name="Иван",
        last_name="Иванов",
    )


@pytest.mark.django_db
def test_login_page(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_successful_login(client, portal_user):
    response = client.post(
        reverse("login"),
        {
            "username": "testemployee",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 302
    assert str(portal_user.pk) == client.session["_auth_user_id"]


@pytest.mark.django_db
def test_invalid_login(client, portal_user):
    response = client.post(
        reverse("login"),
        {
            "username": "testemployee",
            "password": "WrongPassword!",
        },
    )

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get(reverse("profile"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_profile_authenticated(client, portal_user):
    client.force_login(portal_user)

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert b"testemployee" in response.content


@pytest.mark.django_db
def test_remember_me(client, portal_user):
    response = client.post(
        reverse("login"),
        {
            "username": "testemployee",
            "password": "TestPassword123!",
            "remember_me": "on",
        },
    )

    assert response.status_code == 302
    assert client.session.get_expire_at_browser_close() is False

    max_age = client.session.get_expiry_age()
    assert 29 * 24 * 60 * 60 <= max_age <= 30 * 24 * 60 * 60


@pytest.mark.django_db
def test_without_remember_me(client, portal_user):
    response = client.post(
        reverse("login"),
        {
            "username": "testemployee",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 302
    assert client.session.get_expire_at_browser_close() is True


@pytest.mark.django_db
def test_logout_post(client, portal_user):
    client.force_login(portal_user)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_logout_get_not_allowed(client, portal_user):
    client.force_login(portal_user)

    response = client.get(reverse("logout"))

    assert response.status_code == 405
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_anonymous_admin_login_accessible(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_login_redirect_preserves_next(client):
    response = client.get("/contacts/")

    assert response.status_code == 302
    assert response.url == "/accounts/login/?next=/contacts/"


@pytest.mark.django_db
def test_login_returns_to_requested_page(client, portal_user):
    response = client.post(
        reverse("login") + "?next=/contacts/",
        {
            "username": "testemployee",
            "password": "TestPassword123!",
            "next": "/contacts/",
        },
    )

    assert response.status_code == 302
    assert response.url == "/contacts/"


@pytest.mark.django_db
def test_unknown_page_requires_login(client):
    response = client.get("/unknown-private-section/")

    assert response.status_code == 302
    assert reverse("login") in response.url
