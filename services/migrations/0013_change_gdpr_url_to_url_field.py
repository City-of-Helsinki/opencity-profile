# Generated by Django 2.2.10 on 2020-05-13 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0012_merge_20200511_1534"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="gdpr_url",
            field=models.URLField(
                blank=True,
                help_text="Enter the URL of the service. Final URLs are generated by concatenating the url with the profile uuid",
                max_length=2000,
            ),
        ),
    ]
