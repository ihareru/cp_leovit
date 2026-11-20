import re
from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.password_reset_models import PasswordResetCode

from apps.accounts.password_reset_limits import (
    make_cache_key,
)

from apps.accounts.password_reset_rate_models import (
    PasswordResetRateLimit,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def reset_user(django_user_model):
    return django_user_model.objects.create_user(
        username="password_reset_test",
        email="reset@example.com",
        password="OldPassword123!",
    )


@pytest.fixture
def client():
    return Client()


def request_code(client, email):
    return client.post(
        reverse("password_reset_request"),
        {"email": email},
    )


def get_code_from_email():
    assert len(mail.outbox) == 1

    match = re.search(
        r"Код подтверждения:\s*(\d{6})",
        mail.outbox[0].body,
    )

    assert match is not None
    return match.group(1)


def confirm_reset(client, code, password="NewPassword123!"):
    return client.post(
        reverse("password_reset_confirm"),
        {
            "code": code,
            "new_password1": password,
            "new_password2": password,
        },
    )


def test_reset_pages_are_public(client):
    response = client.get(
        reverse("password_reset_request")
    )
    assert response.status_code == 200

    # Без предварительного запроса кода
    # подтверждение перенаправляет на первый шаг.
    response = client.get(
        reverse("password_reset_confirm")
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "password_reset_request"
    )


def test_request_sends_email(client, reset_user):
    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "password_reset_confirm"
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [
        reset_user.email
    ]

    code = get_code_from_email()
    assert len(code) == 6


def test_unknown_email_does_not_send_email(client):
    response = request_code(
        client,
        "unknown@example.com",
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "password_reset_confirm"
    )

    assert len(mail.outbox) == 0


def test_unknown_email_has_same_public_message(
    client,
    reset_user,
):
    response_existing = request_code(
        client,
        reset_user.email,
    )

    existing_messages = [
        str(message)
        for message in list(
            response_existing.wsgi_request._messages
        )
    ]

    other_client = Client()

    response_unknown = request_code(
        other_client,
        "unknown@example.com",
    )

    unknown_messages = [
        str(message)
        for message in list(
            response_unknown.wsgi_request._messages
        )
    ]

    assert existing_messages == unknown_messages


def test_complete_password_reset(client, reset_user):
    request_code(
        client,
        reset_user.email,
    )

    code = get_code_from_email()

    response = confirm_reset(client, code)

    assert response.status_code == 302
    assert response.url == reverse("login")

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "NewPassword123!"
    )

    record = PasswordResetCode.objects.get(
        user=reset_user
    )

    assert record.used_at is not None


def test_wrong_code_does_not_change_password(
    client,
    reset_user,
):
    request_code(client, reset_user.email)

    code = get_code_from_email()

    wrong_code = (
        "000000"
        if code != "000000"
        else "999999"
    )

    response = confirm_reset(
        client,
        wrong_code,
    )

    assert response.status_code == 200

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "OldPassword123!"
    )

    record = PasswordResetCode.objects.get(
        user=reset_user
    )

    assert record.attempts == 1


def test_expired_code_is_rejected(
    client,
    reset_user,
):
    request_code(client, reset_user.email)

    code = get_code_from_email()

    PasswordResetCode.objects.filter(
        user=reset_user
    ).update(
        expires_at=timezone.now()
        - timedelta(seconds=1)
    )

    response = confirm_reset(client, code)

    assert response.status_code == 200

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "OldPassword123!"
    )


def test_used_code_cannot_reset_password_again(
    client,
    reset_user,
):
    request_code(client, reset_user.email)

    code = get_code_from_email()

    first = confirm_reset(
        client,
        code,
        "NewPassword123!",
    )

    assert first.status_code == 302

    # Восстанавливаем email в сессии,
    # чтобы проверить повторное использование.
    session = client.session
    session["password_reset_email"] = reset_user.email
    session.save()

    second = confirm_reset(
        client,
        code,
        "AnotherPassword123!",
    )

    assert second.status_code == 200

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "NewPassword123!"
    )


def test_resend_cooldown(
    client,
    reset_user,
):
    first = request_code(
        client,
        reset_user.email,
    )

    second = request_code(
        client,
        reset_user.email,
    )

    assert first.status_code == 302
    assert second.status_code == 302

    assert len(mail.outbox) == 1

    assert PasswordResetCode.objects.filter(
        user=reset_user
    ).count() == 1


def test_old_authenticated_session_invalidated(
    client,
    reset_user,
):
    old_client = Client()

    old_client.force_login(reset_user)

    response = old_client.get(
        reverse("profile")
    )

    assert response.status_code == 200

    request_code(
        client,
        reset_user.email,
    )

    code = get_code_from_email()

    response = confirm_reset(client, code)

    assert response.status_code == 302

    # После изменения пароля прежняя сессия
    # должна перестать быть авторизованной.
    response = old_client.get(
        reverse("profile")
    )

    assert response.status_code == 302
    assert reverse("login") in response.url


def test_email_send_failure_is_handled(
    client,
    reset_user,
    monkeypatch,
):
    def failing_send_mail(*args, **kwargs):
        raise ConnectionError("SMTP unavailable")

    monkeypatch.setattr(
        "apps.accounts.password_reset_views.send_mail",
        failing_send_mail,
    )

    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "password_reset_confirm"
    )


def test_rate_limit_blocks_email_sending(
    client,
    reset_user,
):

    for _ in range(5):

        response = request_code(
            client,
            reset_user.email,
        )

        assert response.status_code == 302

    # Убираем действие ограничения повторной
    # отправки кода в 60 секунд.
    PasswordResetCode.objects.filter(
        user=reset_user,
    ).update(
        created_at=(
            timezone.now()
            - timedelta(minutes=2)
        ),
    )

    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302

    assert len(mail.outbox) == 1

    key = make_cache_key(
        "email",
        reset_user.email.lower(),
    )

    counter = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert counter.count == 6

    assert PasswordResetCode.objects.filter(
        user=reset_user,
    ).count() == 1



def test_failed_delivery_invalidates_code(
    client,
    reset_user,
    monkeypatch,
):
    def failing_send_mail(*args, **kwargs):
        raise ConnectionError(
            "Exchange unavailable"
        )

    monkeypatch.setattr(
        "apps.accounts.password_reset_views.send_mail",
        failing_send_mail,
    )

    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302

    reset_record = (
        PasswordResetCode.objects
        .filter(user=reset_user)
        .latest("pk")
    )

    assert reset_record.used_at is not None
    assert reset_record.is_valid is False


def test_zero_sent_messages_invalidates_code(
    client,
    reset_user,
    monkeypatch,
):
    monkeypatch.setattr(
        "apps.accounts.password_reset_views.send_mail",
        lambda *args, **kwargs: 0,
    )

    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302

    reset_record = (
        PasswordResetCode.objects
        .filter(user=reset_user)
        .latest("pk")
    )

    assert reset_record.used_at is not None
    assert reset_record.is_valid is False


def test_successful_delivery_keeps_code_valid(
    client,
    reset_user,
):
    response = request_code(
        client,
        reset_user.email,
    )

    assert response.status_code == 302

    reset_record = (
        PasswordResetCode.objects
        .filter(user=reset_user)
        .latest("pk")
    )

    assert reset_record.used_at is None
    assert reset_record.is_valid is True
