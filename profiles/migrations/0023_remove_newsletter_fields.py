# Generated by Django 2.2.10 on 2020-03-30 06:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0022_add_newsletter_options"),
    ]

    operations = [
        migrations.RemoveField(model_name="profile", name="newsletters_via_email",),
        migrations.RemoveField(model_name="profile", name="newsletters_via_sms",),
    ]
