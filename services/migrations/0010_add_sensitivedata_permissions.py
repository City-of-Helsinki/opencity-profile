# Generated by Django 2.2.8 on 2020-02-07 13:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("services", "0009_add_allowed_data_field")]

    operations = [
        migrations.AlterModelOptions(
            name="service",
            options={
                "permissions": (
                    ("can_manage_profiles", "Can manage profiles"),
                    ("can_view_profiles", "Can view profiles"),
                    ("can_manage_sensitivedata", "Can manage sensitive data"),
                    ("can_view_sensitivedata", "Can view sensitive data"),
                )
            },
        ),
        migrations.AlterField(
            model_name="serviceconnection",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_connections",
                to="profiles.Profile",
            ),
        ),
    ]
