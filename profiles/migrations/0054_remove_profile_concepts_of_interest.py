# Generated by Django 2.2.25 on 2021-12-23 09:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0053_remove_legal_relationship"),
    ]

    operations = [
        migrations.RemoveField(model_name="profile", name="concepts_of_interest",),
    ]
