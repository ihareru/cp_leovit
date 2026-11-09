from django.db import migrations


def initialize_counter(apps, schema_editor):
    TicketCounter = apps.get_model("tickets", "TicketCounter")

    TicketCounter.objects.using(schema_editor.connection.alias).get_or_create(
        name="tickets",
        defaults={"last_number": 0},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticketcounter_ticket_ticketduedatehistory'),
    ]

    operations = [
        migrations.RunPython(
            initialize_counter,
            migrations.RunPython.noop,
        ),
    ]
