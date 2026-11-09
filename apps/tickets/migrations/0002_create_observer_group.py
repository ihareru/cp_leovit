from django.db import migrations


def create_observer_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    db_alias = schema_editor.connection.alias

    # Получаем или создаём ContentType.
    # Во время миграций он может ещё отсутствовать.
    content_type, _ = ContentType.objects.using(
        db_alias
    ).get_or_create(
        app_label="tickets",
        model="ticketaccess",
    )

    # Создаём разрешение наблюдателя.
    permission, _ = Permission.objects.using(
        db_alias
    ).get_or_create(
        content_type=content_type,
        codename="view_all_tickets",
        defaults={
            "name": "Может просматривать все заявки",
        },
    )

    # Создаём группу наблюдателей.
    group, _ = Group.objects.using(
        db_alias
    ).get_or_create(
        name="ticket_observers",
    )

    # Назначаем разрешение группе.
    group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_observer_group,
            migrations.RunPython.noop,
        ),
    ]
