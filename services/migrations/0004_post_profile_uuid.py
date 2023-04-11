# Generated by Django 2.2.4 on 2019-11-05 15:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0003_pre_profile_uuid"),
        ("profiles", "0010_switch_profile_to_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="profiles.Profile"
            ),
        )
    ]
