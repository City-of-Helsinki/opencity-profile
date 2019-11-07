# Generated by Django 2.2.4 on 2019-11-05 15:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("youths", "0004_pre_profile_uuid"),
        ("profiles", "0010_switch_profile_to_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="youthprofile",
            name="profile",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="youth_profile",
                to="profiles.Profile",
            ),
        )
    ]