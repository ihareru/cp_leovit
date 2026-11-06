from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """
    Требует авторизацию для всех страниц портала.

    Исключения:
    - страница входа;
    - Django Admin (использует собственную проверку прав).

    Новые разделы автоматически защищены.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path_info

        login_path = reverse("login")
        admin_path = reverse("admin:index")

        if path == login_path:
            return self.get_response(request)

        if path.startswith(admin_path):
            return self.get_response(request)

        login_url = settings.LOGIN_URL

        return redirect(
            f"{reverse(login_url)}?next={request.get_full_path()}"
        )
