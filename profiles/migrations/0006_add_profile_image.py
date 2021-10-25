# Generated by Django 2.0.5 on 2018-09-27 15:02

from django.db import migrations, models

import profiles.models


class Migration(migrations.Migration):

    dependencies = [("profiles", "0005_add_nickname")]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                storage=profiles.models.OverwriteStorage(),
                upload_to=profiles.models.get_user_media_folder,
            ),
        )
    ]
