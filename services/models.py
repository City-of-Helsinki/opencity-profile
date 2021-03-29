import urllib.parse

import requests
from adminsortable.models import SortableMixin
from django.db import models
from django.db.models import Max
from enumfields import EnumField
from parler.models import TranslatableModel, TranslatedFields

from utils.auth import BearerAuth
from utils.models import SerializableMixin

from .enums import ServiceType
from .exceptions import MissingGDPRUrlException


def get_next_data_field_order():
    try:
        return AllowedDataField.objects.all().aggregate(Max("order"))["order__max"] + 1
    except TypeError:
        return 1


class AllowedDataField(TranslatableModel, SortableMixin):
    field_name = models.CharField(max_length=30, unique=True)
    translations = TranslatedFields(label=models.CharField(max_length=64))
    order = models.PositiveIntegerField(
        default=get_next_data_field_order, editable=False, db_index=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.safe_translation_getter("label", super().__str__())


class Service(TranslatableModel):
    service_type = EnumField(
        ServiceType, max_length=32, blank=False, null=True, unique=True
    )
    name = models.CharField(max_length=200, blank=False, null=False, unique=True)
    translations = TranslatedFields(
        title=models.CharField(max_length=64),
        description=models.TextField(max_length=200, blank=True),
    )
    allowed_data_fields = models.ManyToManyField(AllowedDataField)
    created_at = models.DateTimeField(auto_now_add=True)
    gdpr_url = models.CharField(
        max_length=2000,
        blank=True,
        help_text=(
            "Enter the URL of the service. Final URLs are generated by concatenating the url with the profile UUID."
        ),
    )
    gdpr_query_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API query operation scope"
    )
    gdpr_delete_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API delete operation scope"
    )
    implicit_connection = models.BooleanField(
        default=False,
        help_text="If enabled, this service doesn't require explicit service connections to profiles",
    )

    class Meta:
        permissions = (
            ("can_manage_profiles", "Can manage profiles"),
            ("can_view_profiles", "Can view profiles"),
            ("can_manage_sensitivedata", "Can manage sensitive data"),
            ("can_view_sensitivedata", "Can view sensitive data"),
            (
                "can_view_verified_personal_information",
                "Can view verified personal information",
            ),
        )

    def save(self, *args, **kwargs):
        # Convenience for saving Services with only service_type and no name.
        # When service_type is removed from the code base, this should be
        # removed as well and every Service creation requires a name at that point.
        if not self.name and self.service_type:
            self.name = self.service_type.value

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("title", super().__str__())

    def has_connection_to_profile(self, profile):
        """Has this service an implicit or explicit connection to a profile"""
        if self.implicit_connection:
            return True

        return self.serviceconnection_set.filter(profile=profile).exists()


class ServiceClientId(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="client_ids"
    )
    client_id = models.CharField(max_length=256, null=False, blank=False, unique=True)


class ServiceConnection(SerializableMixin):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="service_connections"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service
        )

    serialize_fields = (
        {"name": "service", "accessor": lambda x: getattr(x, "name")},
        {"name": "created_at", "accessor": lambda x: x.strftime("%Y-%m-%d")},
    )

    def download_gdpr_data(self, api_token: str):
        """Download service specific GDPR data by profile.

        API token needs to be for a user that can access information for the related profile on
        on the related GDPR API.
        """
        if self.service.gdpr_url:
            url = urllib.parse.urljoin(self.service.gdpr_url, str(self.profile.pk))
            try:
                response = requests.get(url, auth=BearerAuth(api_token), timeout=5)
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                return {}
        return {}

    def delete_gdpr_data(self, api_token: str, dry_run=False):
        """Delete service specific GDPR data by profile.

        API token needs to be for a user that can access information for the related profile on
        on the related GDPR API.

        Dry run parameter can be used for asking the service if delete is possible.
        An exception will be raised by this method if deletion response from the
        service indicates an error or if GDPR related URLs have not been configured
        for the related service.
        """
        data = {}
        if dry_run:
            data["dry_run"] = True

        if self.service.gdpr_url:
            url = urllib.parse.urljoin(self.service.gdpr_url, str(self.profile.pk))
            response = requests.delete(
                url, auth=BearerAuth(api_token), timeout=5, data=data
            )
            response.raise_for_status()
            return True

        raise MissingGDPRUrlException(
            f"Service {self.service.name} does not define an URL for GDPR removal."
        )
