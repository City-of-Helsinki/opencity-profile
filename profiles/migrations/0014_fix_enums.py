# Generated by Django 2.2.4 on 2019-12-02 20:24

from django.db import migrations
import enumfields.fields
import profiles.enums


class Migration(migrations.Migration):

    dependencies = [("profiles", "0013_change_foreign_key_type")]

    operations = [
        migrations.AlterField(
            model_name="address",
            name="address_type",
            field=enumfields.fields.EnumField(
                enum=profiles.enums.AddressType, max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="email",
            name="email_type",
            field=enumfields.fields.EnumField(
                enum=profiles.enums.EmailType, max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="legalrelationship",
            name="confirmation_degree",
            field=enumfields.fields.EnumField(
                default="none",
                enum=profiles.enums.RepresentativeConfirmationDegree,
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="legalrelationship",
            name="type",
            field=enumfields.fields.EnumField(
                default="custody", enum=profiles.enums.RepresentationType, max_length=30
            ),
        ),
        migrations.AlterField(
            model_name="phone",
            name="phone_type",
            field=enumfields.fields.EnumField(
                enum=profiles.enums.PhoneType, max_length=32
            ),
        ),
    ]