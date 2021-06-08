# Generated by Django 2.2.20 on 2021-05-07 13:01

from django.db import migrations
import encrypted_fields.fields
import profiles.validators


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0044_add_validator_to_vpi_postal_code_field__noop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="country_code",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="An ISO 3166-1 country code.",
                max_length=3,
                validators=[profiles.validators.validate_iso_3166_country_code],
            ),
        ),
    ]
