def can_access_forms(user):
    """
    Проверяет право доступа к разделу Формы.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.has_perm("forms.access_forms")
    )
