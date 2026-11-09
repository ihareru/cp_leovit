from apps.forms.permissions import can_access_forms


def portal_permissions(request):
    return {
        "can_access_forms": can_access_forms(request.user),
    }
