# Generated by Django 2.2.20 on 2021-05-07 07:01

import encrypted_fields.fields
from django.db import migrations, models

import profiles.validators


class Migration(migrations.Migration):

    dependencies = [
        (
            "profiles",
            "0039_change_national_identification_number_hash_key_to_be_a_callable",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="first_name",
            field=models.CharField(
                blank=True,
                help_text="First name(s).",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="given_name",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="The name the person is called with.",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="last_name",
            field=models.CharField(
                blank=True,
                help_text="Last name.",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformation",
            name="municipality_of_residence",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="Official municipality of residence in Finland as a free form text.",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="post_office",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentaddress",
            name="street_address",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="additional_address",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="Additional address information, perhaps town, county, state, country etc.",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationpermanentforeignaddress",
            name="street_address",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                help_text="Street address or whatever is the _first part_ of the address.",
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="post_office",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
        migrations.AlterField(
            model_name="verifiedpersonalinformationtemporaryaddress",
            name="street_address",
            field=encrypted_fields.fields.EncryptedCharField(
                blank=True,
                max_length=1024,
                validators=[profiles.validators.validate_visible_latin_characters_only],
            ),
        ),
    ]
