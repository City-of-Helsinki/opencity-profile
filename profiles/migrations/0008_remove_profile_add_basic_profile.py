# Generated by Django 2.2.3 on 2019-10-23 07:37

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import profiles.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("thesaurus", "0001_initial"),
        ("munigeo", "0005_auto_20191023_1016"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profiles", "0007_add_legal_relationship_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="BasicProfile",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "first_name",
                    models.CharField(max_length=40, verbose_name="first name"),
                ),
                (
                    "last_name",
                    models.CharField(max_length=150, verbose_name="last name"),
                ),
                ("dob", models.DateField(verbose_name="date of birth")),
                ("address", models.CharField(max_length=150, verbose_name="address")),
                ("zip_code", models.CharField(max_length=64, verbose_name="zip code")),
                (
                    "municipality",
                    models.CharField(max_length=64, verbose_name="municipality"),
                ),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("phone", models.CharField(blank=True, max_length=255, null=True)),
                ("nickname", models.CharField(blank=True, max_length=32, null=True)),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=profiles.models.OverwriteStorage(),
                        upload_to=profiles.models.get_user_media_folder,
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("fi", "Finnish"),
                            ("en", "English"),
                            ("sv", "Swedish"),
                        ],
                        default="fi",
                        max_length=7,
                    ),
                ),
                (
                    "contact_method",
                    models.CharField(
                        choices=[("email", "Email"), ("sms", "SMS")],
                        default="email",
                        max_length=30,
                    ),
                ),
                (
                    "preferences",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, null=True
                    ),
                ),
                (
                    "concepts_of_interest",
                    models.ManyToManyField(blank=True, to="thesaurus.Concept"),
                ),
                (
                    "divisions_of_interest",
                    models.ManyToManyField(
                        blank=True, to="munigeo.AdministrativeDivision"
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.RemoveField(model_name="profile", name="concepts_of_interest"),
        migrations.RemoveField(model_name="profile", name="divisions_of_interest"),
        migrations.RemoveField(model_name="profile", name="legal_relationships"),
        migrations.RemoveField(model_name="profile", name="user"),
        migrations.DeleteModel(name="LegalRelationship"),
        migrations.DeleteModel(name="Profile"),
    ]
