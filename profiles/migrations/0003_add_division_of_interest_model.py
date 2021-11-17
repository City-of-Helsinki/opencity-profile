# Generated by Django 2.0.5 on 2018-09-17 14:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("munigeo", "0004_delete_old_translations"),
        ("profiles", "0002_add_munigeo_districts_to_profile"),
    ]

    operations = [
        migrations.CreateModel(
            name="DivisionOfInterest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "division",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="division_of_interest",
                        to="munigeo.AdministrativeDivision",
                    ),
                ),
            ],
        )
    ]
