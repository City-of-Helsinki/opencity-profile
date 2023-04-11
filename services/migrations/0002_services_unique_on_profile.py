# Generated by Django 2.2.3 on 2019-10-31 10:56

from django.db import migrations
from django.db.models import Count, Min


def remove_duplicate_services_for_profiles(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    master_pks = (
        Service.objects.values("profile_id", "service_type")
        .annotate(Min("pk"), count=Count("pk"))
        .filter(count__gt=1)
        .values_list("pk__min", flat=True)
    )

    masters = Service.objects.in_bulk(list(master_pks))

    for master in masters.values():
        Service.objects.filter(
            profile_id=master.profile_id, service_type=master.service_type
        ).exclude(pk=master.pk).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0008_add_first_name_and_last_name_to_profile"),
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            remove_duplicate_services_for_profiles, migrations.RunPython.noop
        ),
        migrations.AlterUniqueTogether(
            name="service", unique_together={("profile", "service_type")}
        ),
    ]
