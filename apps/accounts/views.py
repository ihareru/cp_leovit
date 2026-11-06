from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.urls import reverse_lazy

from .forms import PortalAuthenticationForm


class PortalLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = PortalAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)

        remember_me = form.cleaned_data.get(
            "remember_me",
            False,
        )

        if remember_me:
            self.request.session.set_expiry(
                60 * 60 * 24 * 30
            )
        else:
            self.request.session.set_expiry(0)

        return response


@login_required
def profile(request):
    return render(
        request,
        "accounts/profile.html",
    )
