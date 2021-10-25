# Generated by Django 2.2.22 on 2021-05-14 08:17

from django.db import migrations

import profiles.models
import profiles.validators


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0045_add_validator_to_vpi_country_code_field__noop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="_national_identification_number_data",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[
                    profiles.validators.validate_finnish_national_identification_number
                ],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="email",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True, help_text="Email.", max_length=1024
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="first_name",
            field=profiles.models.NullToEmptyCharField(
                blank=True,
                help_text="First name(s).",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="given_name",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="The name the person is called with.",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="last_name",
            field=profiles.models.NullToEmptyCharField(
                blank=True,
                help_text="Last name.",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="municipality_of_residence",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="Official municipality of residence in Finland as a free form text.",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="municipality_of_residence_number",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="Official municipality of residence in Finland as an official number.",
                max_length=3,
                validators=[
                    profiles.validators.validate_finnish_municipality_of_residence_number
                ],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="national_identification_number",
            field=profiles.models.NullToEmptyEncryptedSearchField(
                blank=True,
                db_index=True,
                encrypted_field_name="_national_identification_number_data",
                hash_key=profiles.models.get_national_identification_number_hash_key,
                help_text="Finnish national identification number.",
                max_length=66,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="post_office",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="postal_code",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_finnish_postal_code],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="street_address",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="additional_address",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="Additional address information, perhaps town, county, state, country etc.",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="country_code",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="An ISO 3166-1 country code.",
                max_length=3,
                validators=[profiles.validators.validate_iso_3166_country_code],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="street_address",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                help_text="Street address or whatever is the _first part_ of the address.",
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="post_office",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="postal_code",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_finnish_postal_code],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="street_address",
            field=profiles.models.NullToEmptyEncryptedCharField(
                blank=True,
                max_length=100,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
    ]
