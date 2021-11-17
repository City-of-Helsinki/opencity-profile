# Generated by Django 2.2.20 on 2021-05-07 08:38

import encrypted_fields.fields
from django.db import migrations

import profiles.validators


class Migration(migrations.Migration):

    dependencies = [
        (
            "profiles",
            "0043_add_validator_to_vpi_municipality_of_residence_number_field__noop",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="postal_code",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_finnish_postal_code],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="postal_code",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_finnish_postal_code],
            ),
        ),
    ]
