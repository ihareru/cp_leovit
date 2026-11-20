import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .password_reset_forms import (
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
)
from .password_reset_service import (
    ResetCodeCooldown,
    ResetCodeInvalid,
    create_reset_code_record,
    invalidate_reset_code,
    reset_password_with_code,
)
from .password_reset_limits import (
    check_reset_confirm_limits,
    check_reset_request_limits,
)


logger = logging.getLogger(__name__)

SESSION_EMAIL_KEY = "password_reset_email"

GENERIC_MESSAGE = (
    "Если указанный адрес зарегистрирован, "
    "на него отправлен код восстановления."
)

class PasswordResetDeliveryError(Exception):
    """Не удалось отправить код восстановления."""


@never_cache
@require_http_methods(["GET", "POST"])
def password_reset_request(request):

    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]

            allowed = check_reset_request_limits(
                request,
                email,
            )

            User = get_user_model()

            user = User.objects.filter(
                email__iexact=email,
                is_active=True,
            ).first()

            if allowed and user is not None:

                reset_result = None

                try:
                    reset_result = (
                        create_reset_code_record(user)
                    )

                    sent_count = send_mail(
                        subject=(
                            "Leovit — восстановление пароля"
                        ),
                        message=(
                            "Вы запросили восстановление "
                            "пароля корпоративного портала.\n\n"
                            f"Код подтверждения: "
                            f"{reset_result.code}\n\n"
                            "Код действует 15 минут.\n\n"
                            "Если вы не запрашивали "
                            "восстановление пароля, "
                            "проигнорируйте это письмо."
                        ),
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )

                    if sent_count != 1:
                        raise PasswordResetDeliveryError(
                            "Почтовый backend не подтвердил "
                            "отправку сообщения."
                        )

                except ResetCodeCooldown:
                    pass

                except Exception as exc:

                    if reset_result is not None:
                        invalidate_reset_code(
                            reset_result.record_id
                        )

                    logger.error(
                        "Ошибка отправки кода "
                        "восстановления для пользователя "
                        "id=%s, тип ошибки=%s",
                        user.pk,
                        type(exc).__name__,
                    )

            request.session.cycle_key()

            request.session[SESSION_EMAIL_KEY] = email

            messages.success(
                request,
                GENERIC_MESSAGE,
            )

            return redirect(
                "password_reset_confirm"
            )

    else:
        form = PasswordResetRequestForm()

    return render(
        request,
        "registration/password_reset_request.html",
        {
            "form": form,
        },
    )




@never_cache
@require_http_methods(["GET", "POST"])
def password_reset_confirm(request):

    email = request.session.get(
        SESSION_EMAIL_KEY
    )

    if not email:

        return redirect(
            "password_reset_request"
        )

    User = get_user_model()

    if request.method == "POST":

        form = PasswordResetConfirmForm(
            request.POST
        )

        # Учитываем все POST-запросы,
        # включая некорректно заполненные формы.
        allowed = check_reset_confirm_limits(
            request,
            email,
        )

        if not allowed:

            form.is_valid()

            form.add_error(
                None,
                (
                    "Слишком много попыток. "
                    "Повторите попытку позже."
                ),
            )

        elif form.is_valid():

            user = User.objects.filter(
                email__iexact=email,
                is_active=True,
            ).first()

            if user is None:

                form.add_error(
                    "code",
                    "Неверный или недействительный код.",
                )

            else:

                try:

                    success = reset_password_with_code(
                        user=user,
                        code=form.cleaned_data["code"],
                        new_password=(
                            form.cleaned_data[
                                "new_password1"
                            ]
                        ),
                    )

                except ResetCodeInvalid:

                    success = False

                except ValidationError as exc:

                    form.add_error(
                        "new_password1",
                        exc,
                    )

                    success = False

                if success:

                    request.session.pop(
                        SESSION_EMAIL_KEY,
                        None,
                    )

                    messages.success(
                        request,
                        (
                            "Пароль успешно изменён. "
                            "Теперь вы можете войти."
                        ),
                    )

                    return redirect("login")

                if not form.errors:

                    form.add_error(
                        "code",
                        (
                            "Неверный или "
                            "недействительный код."
                        ),
                    )

    else:

        form = PasswordResetConfirmForm()

    return render(
        request,
        "registration/password_reset_confirm.html",
        {
            "form": form,
        },
    )
