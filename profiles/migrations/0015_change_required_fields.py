# Generated by Django 2.2.4 on 2019-12-10 11:25

import enumfields.fields
from django.db import migrations, models

import profiles.enums


class Migration(migrations.Migration):

    dependencies = [("profiles", "0014_fix_enums")]

    operations = [
        migrations.AlterField(
            model_name="address",
            name="address_type",
            field=enumfields.fields.EnumField(
                default="home", enum=profiles.enums.AddressType, max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="country_code",
            field=models.CharField(max_length=2),
        ),
        migrations.AlterField(
            model_name="email", name="email", field=models.EmailField(max_length=254)
        ),
        migrations.AlterField(
            model_name="email",
            name="email_type",
            field=enumfields.fields.EnumField(
                default="personal", enum=profiles.enums.EmailType, max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="phone",
            name="phone_type",
            field=enumfields.fields.EnumField(
                default="mobile", enum=profiles.enums.PhoneType, max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="language",
            field=models.CharField(
                choices=[("fi", "Finnish"), ("en", "English"), ("sv", "Swedish")],
                default="fi",
                max_length=2,
            ),
        ),
    ]
