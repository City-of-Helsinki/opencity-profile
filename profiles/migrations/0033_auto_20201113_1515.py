# Generated by Django 2.2.13 on 2020-11-13 13:15

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0032_verifiedpersonalinformationpermanentforeignaddress"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="verifiedpersonalinformation",
            options={
                "permissions": [
                    (
                        "manage_verified_personal_information",
                        "Can manage verified personal information",
                    )
                ]
            },
        ),
    ]
