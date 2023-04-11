# Generated by Django 2.2.24 on 2021-09-29 12:37

from django.db import migrations

import profiles.validators
import utils.fields


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0050_change_name_fields_to_null_to_empty_value_fields__noop"),
    ]

    operations = [
        migrations.AlterField(
            model_name="address",
            name="address",
            field=utils.fields.NullToEmptyCharField(blank=True, max_length=128),
        ),
        migrations.AlterField(
            model_name="address",
            name="city",
            field=utils.fields.NullToEmptyCharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="address",
            name="country_code",
            field=utils.fields.NullToEmptyCharField(
                blank=True,
                max_length=2,
                validators=[profiles.validators.validate_iso_3166_alpha_2_country_code],
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="postal_code",
            field=utils.fields.NullToEmptyCharField(blank=True, max_length=32),
        ),
    ]
