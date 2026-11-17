
import pytest

from apps.accounts.admin_forms import (
    PortalUserChangeForm,
    PortalUserCreationForm,
)
from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_without_email():
    form = PortalUserCreationForm(
        data={
            "username": "new_user",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "email": "",
        }
    )

    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_create_user_with_duplicate_email():
    User.objects.create_user(
        username="first_user",
        email="user@example.com",
        password="StrongPassword123!",
    )

    form = PortalUserCreationForm(
        data={
            "username": "second_user",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "email": "USER@example.com",
        }
    )

    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_email_normalization():
    form = PortalUserCreationForm(
        data={
            "username": "new_user",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "email": "USER@EXAMPLE.COM",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["email"] == "user@example.com"


@pytest.mark.django_db
def test_user_can_keep_existing_email():
    user = User.objects.create_user(
        username="existing_user",
        email="user@example.com",
        password="StrongPassword123!",
    )

    form = PortalUserChangeForm(
        instance=user,
        data={
            "username": user.username,
            "email": "USER@example.com",
            "is_active": True,
            "date_joined": user.date_joined.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        },
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["email"] == "user@example.com"
