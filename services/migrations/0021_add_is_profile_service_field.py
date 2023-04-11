# Generated by Django 2.2.24 on 2021-10-19 05:44

import logging

from django.db import migrations, models


def set_implicit_connection_service_as_profile_service(apps, schema_editor):
    Service = apps.get_model("services", "Service")

    implicit_connection_services = Service.objects.filter(implicit_connection=True)

    num_implicit_connection_services = implicit_connection_services.count()

    if num_implicit_connection_services == 1:
        implicit_connection_service = implicit_connection_services.get()
        implicit_connection_service.is_profile_service = True
        implicit_connection_service.save()
    elif num_implicit_connection_services > 1:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Can not set Profile Service automatically because there are more than one Service "
            "with implicit_connection set to True. The Profile Service needs to be set manually."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0020_change_gdpr_url_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="is_profile_service",
            field=models.BooleanField(
                default=False,
                help_text="Identifies the profile service itself. Only one Service can have this property.",
            ),
        ),
        migrations.AddConstraint(
            model_name="service",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_profile_service=True),
                fields=("is_profile_service",),
                name="unique_is_profile_service",
            ),
        ),
        migrations.RunPython(
            set_implicit_connection_service_as_profile_service,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
