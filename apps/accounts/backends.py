from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Авторизация пользователя по email и паролю.
    """

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs,
    ):
        if username is None:
            username = kwargs.get("email")

        if not username or password is None:
            return None

        User = get_user_model()

        try:
            user = User.objects.get(
                email__iexact=username.strip()
            )
        except (
            User.DoesNotExist,
            User.MultipleObjectsReturned,
        ):
            User().set_password(password)
            return None

        if (
            user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None
