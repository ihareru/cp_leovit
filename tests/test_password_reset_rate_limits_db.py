
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from django.db import (
    DatabaseError,
    close_old_connections,
    connection,
    connections,
)

from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.password_reset_limits import (
    MAX_REQUESTS_PER_EMAIL,
    MAX_REQUESTS_PER_IP,
    WINDOW_SECONDS,
    check_reset_request_limits,
    get_client_ip,
    increment_counter,
    make_cache_key,
)

from apps.accounts.password_reset_rate_models import (
    PasswordResetRateLimit,
)


pytestmark = pytest.mark.django_db(
    transaction=True,
)


def run_parallel(worker, count):

    barrier = Barrier(count)

    def execute(index):

        close_old_connections()

        try:
            barrier.wait(timeout=30)

            return worker(index)

        finally:
            connections.close_all()

    with ThreadPoolExecutor(
        max_workers=count,
    ) as executor:

        return list(
            executor.map(
                execute,
                range(count),
            )
        )


def test_database_is_postgresql():

    assert connection.vendor == "postgresql"


def test_new_counter_is_created():

    key = make_cache_key(
        "email",
        "employee@example.com",
    )

    assert increment_counter(key) == 1

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 1

    assert record.expires_at > timezone.now()


def test_existing_counter_is_incremented():

    key = make_cache_key(
        "email",
        "employee@example.com",
    )

    assert increment_counter(key) == 1
    assert increment_counter(key) == 2
    assert increment_counter(key) == 3

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 3


def test_expired_counter_is_reset():

    key = make_cache_key(
        "email",
        "employee@example.com",
    )

    now = timezone.now()

    PasswordResetRateLimit.objects.create(
        key=key,
        count=100,
        expires_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(minutes=16),
    )

    assert increment_counter(key) == 1

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 1

    assert record.expires_at >= (
        now + timedelta(seconds=WINDOW_SECONDS)
    )


def test_increment_does_not_extend_active_window():

    key = make_cache_key(
        "email",
        "employee@example.com",
    )

    increment_counter(key)

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    original_expiration = record.expires_at

    increment_counter(key)

    record.refresh_from_db()

    assert record.expires_at == original_expiration

    assert record.count == 2


def test_different_keys_have_separate_counters():

    first_key = make_cache_key(
        "email",
        "first@example.com",
    )

    second_key = make_cache_key(
        "email",
        "second@example.com",
    )

    increment_counter(first_key)
    increment_counter(first_key)

    increment_counter(second_key)

    assert PasswordResetRateLimit.objects.get(
        key=first_key,
    ).count == 2

    assert PasswordResetRateLimit.objects.get(
        key=second_key,
    ).count == 1


def test_ipv6_mapped_address_is_normalized():

    request = RequestFactory().post(
        "/accounts/password-reset/",
        REMOTE_ADDR="::ffff:192.168.1.100",
    )

    assert get_client_ip(request) == (
        "192.168.1.100"
    )


def test_database_failure_blocks_request(
    monkeypatch,
):

    def fail(*args, **kwargs):

        raise DatabaseError(
            "Database error"
        )

    monkeypatch.setattr(
        "apps.accounts.password_reset_limits."
        "increment_counter",
        fail,
    )

    request = RequestFactory().post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    assert check_reset_request_limits(
        request,
        "employee@example.com",
    ) is False


def test_second_counter_failure_rolls_back_first(
    monkeypatch,
):

    original_increment = increment_counter

    def fail_on_email(key):

        if key.startswith(
            "password_reset:email:"
        ):
            raise DatabaseError(
                "Email counter error"
            )

        return original_increment(key)

    monkeypatch.setattr(
        "apps.accounts.password_reset_limits."
        "increment_counter",
        fail_on_email,
    )

    request = RequestFactory().post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    assert check_reset_request_limits(
        request,
        "employee@example.com",
    ) is False

    assert not PasswordResetRateLimit.objects.exists()


def test_parallel_counter_creation_and_increment():

    key = make_cache_key(
        "email",
        "parallel@example.com",
    )

    def worker(index):

        return increment_counter(key)

    results = run_parallel(
        worker,
        10,
    )

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 10

    assert sorted(results) == list(
        range(1, 11),
    )

    assert PasswordResetRateLimit.objects.filter(
        key=key,
    ).count() == 1


def test_parallel_email_requests_respect_limit():

    email = "parallel@example.com"

    def worker(index):

        request = RequestFactory().post(
            "/accounts/password-reset/",
            REMOTE_ADDR=f"192.168.10.{index + 1}",
        )

        return check_reset_request_limits(
            request,
            email,
        )

    results = run_parallel(
        worker,
        10,
    )

    assert results.count(True) == (
        MAX_REQUESTS_PER_EMAIL
    )

    assert results.count(False) == 5

    key = make_cache_key(
        "email",
        email,
    )

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 10


def test_parallel_ip_requests_respect_limit():

    ip = "192.168.1.100"

    key = make_cache_key(
        "ip",
        ip,
    )

    for _ in range(
        MAX_REQUESTS_PER_IP - 5
    ):
        increment_counter(key)

    def worker(index):

        request = RequestFactory().post(
            "/accounts/password-reset/",
            REMOTE_ADDR=ip,
        )

        return check_reset_request_limits(
            request,
            f"employee{index}@example.com",
        )

    results = run_parallel(
        worker,
        10,
    )

    assert results.count(True) == 5
    assert results.count(False) == 5

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == (
        MAX_REQUESTS_PER_IP + 5
    )


def test_blocked_ip_does_not_create_email_counter():

    ip = "192.168.1.100"

    ip_key = make_cache_key(
        "ip",
        ip,
    )

    for _ in range(MAX_REQUESTS_PER_IP):

        increment_counter(ip_key)

    request = RequestFactory().post(
        "/accounts/password-reset/",
        REMOTE_ADDR=ip,
    )

    email = "blocked@example.com"

    assert check_reset_request_limits(
        request,
        email,
    ) is False

    email_key = make_cache_key(
        "email",
        email,
    )

    assert not PasswordResetRateLimit.objects.filter(
        key=email_key,
    ).exists()


def test_email_normalization_uses_same_counter():

    request = RequestFactory().post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    assert check_reset_request_limits(
        request,
        " Employee@Example.com ",
    ) is True

    assert check_reset_request_limits(
        request,
        "employee@example.com",
    ) is True

    key = make_cache_key(
        "email",
        "employee@example.com",
    )

    record = PasswordResetRateLimit.objects.get(
        key=key,
    )

    assert record.count == 2
