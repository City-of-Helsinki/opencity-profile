# Generated by Django 2.2.10 on 2020-06-10 07:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0025_fix_primary_emails"),
    ]

    operations = [
        migrations.AddField(
            model_name="email",
            name="verified",
            field=models.BooleanField(default=False),
        ),
    ]
