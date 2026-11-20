
import pytest

from django.core import mail
from django.db import DatabaseError
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts.password_reset_limits import (
    check_reset_confirm_limits,
    check_reset_request_limits,
    make_cache_key,
)

from apps.accounts.password_reset_models import (
    PasswordResetCode,
)

from apps.accounts.password_reset_rate_models import (
    PasswordResetRateLimit,
)

from apps.accounts.password_reset_views import (
    SESSION_EMAIL_KEY,
)


pytestmark = pytest.mark.django_db


EMAIL = "confirm@example.com"

OLD_PASSWORD = "OldPassword123!"


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def user(django_user_model):

    return django_user_model.objects.create_user(
        username="confirm_limit_test",
        email=EMAIL,
        password=OLD_PASSWORD,
    )


@pytest.fixture
def reset_client(user):

    client = Client()

    response = client.post(
        reverse("password_reset_request"),
        {
            "email": user.email,
        },
    )

    assert response.status_code == 302

    return client


def test_confirmation_email_limit(
    factory,
    settings,
):

    settings.PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = 3

    request = factory.post(
        "/",
        REMOTE_ADDR="192.168.1.50",
    )

    for _ in range(3):

        assert check_reset_confirm_limits(
            request,
            EMAIL,
        ) is True

    assert check_reset_confirm_limits(
        request,
        EMAIL,
    ) is False


def test_confirmation_ip_limit(
    factory,
    settings,
):

    settings.PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP = 3

    request = factory.post(
        "/",
        REMOTE_ADDR="192.168.1.50",
    )

    for index in range(3):

        assert check_reset_confirm_limits(
            request,
            f"user{index}@example.com",
        ) is True

    assert check_reset_confirm_limits(
        request,
        "another@example.com",
    ) is False


def test_confirmation_email_limit_across_ips(
    factory,
    settings,
):

    settings.PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = 3

    for index in range(3):

        request = factory.post(
            "/",
            REMOTE_ADDR=f"192.168.1.{index + 1}",
        )

        assert check_reset_confirm_limits(
            request,
            EMAIL,
        ) is True

    request = factory.post(
        "/",
        REMOTE_ADDR="192.168.2.10",
    )

    assert check_reset_confirm_limits(
        request,
        EMAIL,
    ) is False


def test_request_and_confirm_counters_are_independent(
    factory,
):

    request = factory.post(
        "/",
        REMOTE_ADDR="192.168.1.50",
    )

    for _ in range(5):

        assert check_reset_request_limits(
            request,
            EMAIL,
        ) is True

    assert check_reset_request_limits(
        request,
        EMAIL,
    ) is False

    assert check_reset_confirm_limits(
        request,
        EMAIL,
    ) is True


def test_confirmation_database_failure(
    factory,
    monkeypatch,
):

    def fail(*args, **kwargs):

        raise DatabaseError(
            "Database unavailable"
        )

    monkeypatch.setattr(
        "apps.accounts.password_reset_limits."
        "increment_counter",
        fail,
    )

    request = factory.post(
        "/",
        REMOTE_ADDR="192.168.1.50",
    )

    assert check_reset_confirm_limits(
        request,
        EMAIL,
    ) is False


def test_get_request_does_not_consume_limit(
    reset_client,
):

    response = reset_client.get(
        reverse("password_reset_confirm"),
    )

    assert response.status_code == 200

    key = make_cache_key(
        "confirm_email",
        EMAIL,
    )

    assert not PasswordResetRateLimit.objects.filter(
        key=key,
    ).exists()


def test_invalid_form_consumes_limit(
    reset_client,
):

    response = reset_client.post(
        reverse("password_reset_confirm"),
        {
            "code": "",
            "new_password1": "",
            "new_password2": "",
        },
    )

    assert response.status_code == 200

    key = make_cache_key(
        "confirm_email",
        EMAIL,
    )

    counter = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert counter.count == 1


def test_blocked_confirmation_does_not_call_service(
    reset_client,
    settings,
    monkeypatch,
):

    settings.PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = 1

    reset_client.post(
        reverse("password_reset_confirm"),
        {},
    )

    def unexpected_call(*args, **kwargs):

        pytest.fail(
            "Reset service must not be called."
        )

    monkeypatch.setattr(
        "apps.accounts.password_reset_views."
        "reset_password_with_code",
        unexpected_call,
    )

    response = reset_client.post(
        reverse("password_reset_confirm"),
        {
            "code": "123456",
            "new_password1": "NewPassword456!",
            "new_password2": "NewPassword456!",
        },
    )

    assert response.status_code == 200

    assert (
        "Слишком много попыток."
        in response.content.decode()
    )


def test_blocked_confirmation_does_not_change_password(
    reset_client,
    user,
    settings,
):

    import re

    settings.PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = 1

    reset_client.post(
        reverse("password_reset_confirm"),
        {},
    )

    code = re.search(
        r"Код подтверждения:\s*(\d{6})",
        mail.outbox[0].body,
    ).group(1)

    response = reset_client.post(
        reverse("password_reset_confirm"),
        {
            "code": code,
            "new_password1": "NewPassword456!",
            "new_password2": "NewPassword456!",
        },
    )

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.check_password(
        OLD_PASSWORD,
    )

    record = PasswordResetCode.objects.get(
        user=user,
    )

    assert record.used_at is None


def test_unknown_email_also_consumes_limit():

    client = Client()

    session = client.session

    session[SESSION_EMAIL_KEY] = (
        "unknown@example.com"
    )

    session.save()

    response = client.post(
        reverse("password_reset_confirm"),
        {
            "code": "123456",
            "new_password1": "NewPassword456!",
            "new_password2": "NewPassword456!",
        },
    )

    assert response.status_code == 200

    key = make_cache_key(
        "confirm_email",
        "unknown@example.com",
    )

    counter = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert counter.count == 1
