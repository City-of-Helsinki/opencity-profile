import urllib.parse
from dataclasses import dataclass
from json import JSONDecodeError
from string import Template
from typing import List

import requests
from adminsortable.models import SortableMixin
from django.db import models
from django.db.models import Max, Q
from enumfields import EnumField
from parler.models import TranslatableModel, TranslatedFields

from open_city_profile.consts import (
    SERVICE_GDPR_API_REQUEST_ERROR,
    SERVICE_GDPR_API_UNKNOWN_ERROR,
)
from utils.auth import BearerAuth
from utils.models import SerializableMixin

from .enums import ServiceType


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
        description=models.TextField(max_length=500, blank=True),
    )
    allowed_data_fields = models.ManyToManyField(AllowedDataField)
    created_at = models.DateTimeField(auto_now_add=True)
    gdpr_url = models.CharField(
        max_length=2000,
        blank=True,
        help_text=(
            'The URL of the Service\'s GDPR endpoint. Tokens "$profile_id" or'
            ' "$user_uuid" will be replaced with the corresponding value.'
            " Otherwise the Profile ID will be automatically appended to the url."
        ),
    )
    gdpr_query_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API query operation scope"
    )
    gdpr_delete_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API delete operation scope"
    )
    is_profile_service = models.BooleanField(
        default=False,
        help_text="Identifies the profile service itself. Only one Service can have this property.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_profile_service"],
                condition=Q(is_profile_service=True),
                name="unique_is_profile_service",
            )
        ]
        ordering = ["id"]
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
        return (
            self.is_profile_service
            or self.serviceconnection_set.filter(profile=profile).exists()
        )

    def get_gdpr_url_for_profile(self, profile):
        if not self.gdpr_url or not profile:
            return None

        url_template = Template(self.gdpr_url)
        mapping = {"profile_id": profile.id}
        if profile.user:
            mapping["user_uuid"] = profile.user.uuid
        else:
            # If the template has a reference to user_uuid and there is no user
            # the GDPR URL cannot be generated.
            for match in url_template.pattern.finditer(url_template.template):
                if (
                    match.group("named") == "user_uuid"
                    or match.group("braced") == "user_uuid"
                ):
                    return None

        gdpr_url = url_template.safe_substitute(mapping)

        if gdpr_url == self.gdpr_url:
            return urllib.parse.urljoin(self.gdpr_url, str(profile.pk))

        return gdpr_url


class ServiceClientId(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="client_ids"
    )
    client_id = models.CharField(max_length=256, null=False, blank=False, unique=True)


def _validate_gdpr_api_errors(errors):
    try:
        iter(errors)
    except TypeError:
        return False

    expected_keys = {"code", "message"}
    for error in errors:
        if set(error.keys()) != expected_keys:
            return False
        if not error.get("code") or not isinstance(error["code"], str):
            return False
        if not error.get("message") or not isinstance(error["message"], dict):
            return False

        for key, value in error["message"].items():
            if not key or not isinstance(value, str):
                return False

    return True


@dataclass
class DeleteGdprDataErrorMessage:
    lang: str
    text: str


@dataclass
class DeleteGdprDataError:
    code: str
    message: List[DeleteGdprDataErrorMessage]


@dataclass
class DeleteGdprDataResult:
    service: Service
    dry_run: bool
    success: bool
    errors: List[DeleteGdprDataError]


def _convert_gdpr_api_errors(errors) -> List[DeleteGdprDataError]:
    """Converts errors from the GDPR API to a list of DeleteGdprDataErrors"""
    converted_errors = []
    for error in errors:
        converted_error = DeleteGdprDataError(code=error["code"], message=[])
        for lang, text in error["message"].items():
            converted_error.message.append(
                DeleteGdprDataErrorMessage(lang=lang, text=text)
            )
        converted_errors.append(converted_error)

    return converted_errors


def _add_error_to_result(result, code, message):
    result.errors.append(
        DeleteGdprDataError(
            code=code, message=[DeleteGdprDataErrorMessage(lang="en", text=message)]
        )
    )

    return result


class ServiceConnection(SerializableMixin):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="service_connections"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")
        ordering = ["id"]

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

        API token needs to be for a user that can access information for the related
        profile on the related GDPR API.
        """
        url = self.service.get_gdpr_url_for_profile(self.profile)
        if url:
            try:
                response = requests.get(url, auth=BearerAuth(api_token), timeout=5)
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                return {}
        return {}

    def delete_gdpr_data(self, api_token: str, dry_run=False) -> DeleteGdprDataResult:
        """Delete service specific GDPR data by profile.

        API token needs to be for a user that can access information for the related
        profile on the related GDPR API.

        Dry run parameter can be used for asking the service if delete is possible.

        The errors content from the service is returned if the service provides a JSON
        response with an "errors" key containing valid error content.
        """
        result = DeleteGdprDataResult(
            service=self.service, dry_run=dry_run, success=False, errors=[],
        )

        url = self.service.get_gdpr_url_for_profile(self.profile)

        data = {}
        if dry_run:
            data["dry_run"] = True

        try:
            response = requests.delete(
                url, auth=BearerAuth(api_token), timeout=5, data=data
            )
        except requests.RequestException:
            return _add_error_to_result(
                result,
                SERVICE_GDPR_API_REQUEST_ERROR,
                "Error when making a request to the GDPR URL of the service",
            )

        if response.status_code == 204:
            result.success = True
            return result

        if response.status_code in [403, 500]:
            try:
                errors_from_the_service = response.json().get("errors")
                if _validate_gdpr_api_errors(errors_from_the_service):
                    result.errors = _convert_gdpr_api_errors(errors_from_the_service)
                    return result
            except JSONDecodeError:
                pass

        return _add_error_to_result(
            result,
            SERVICE_GDPR_API_UNKNOWN_ERROR,
            "Unknown error occurred when trying to remove data from the service",
        )
