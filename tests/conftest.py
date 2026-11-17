import pytest


@pytest.fixture(autouse=True)
def assign_email_to_test_users(monkeypatch, django_user_model):
    """
    Автоматически назначает уникальный email
    тестовым пользователям, если он не указан.

    Действует только во время pytest.
    """

    manager = django_user_model._default_manager
    original_create_user = manager.create_user
    original_create_superuser = manager.create_superuser

    def create_user_with_email(*args, **kwargs):
        username = kwargs.get("username")

        if username is None and args:
            username = args[0]

        if not kwargs.get("email") and username:
            kwargs["email"] = f"{username.lower()}@example.com"

        return original_create_user(*args, **kwargs)

    def create_superuser_with_email(*args, **kwargs):
        username = kwargs.get("username")

        if username is None and args:
            username = args[0]

        if not kwargs.get("email") and username:
            kwargs["email"] = f"{username.lower()}@example.com"

        return original_create_superuser(*args, **kwargs)

    monkeypatch.setattr(
        manager,
        "create_user",
        create_user_with_email,
    )
    monkeypatch.setattr(
        manager,
        "create_superuser",
        create_superuser_with_email,
    )
