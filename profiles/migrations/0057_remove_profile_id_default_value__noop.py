# Generated by Django 3.2.13 on 2022-05-02 10:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0056_change_ordering__noop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="id",
            field=models.UUIDField(editable=False, primary_key=True, serialize=False),
        ),
    ]
