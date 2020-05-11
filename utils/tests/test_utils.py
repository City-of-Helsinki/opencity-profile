import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django_ilmoitin.models import NotificationTemplate
from faker import Faker
from guardian.shortcuts import get_group_perms

from open_city_profile.tests.factories import GroupFactory, UserFactory
from profiles.models import Profile
from services.enums import ServiceType
from services.models import AllowedDataField, Service
from services.tests.factories import ServiceFactory
from users.models import User
from utils.utils import (
    assign_permissions,
    create_user,
    DATA_FIELD_VALUES,
    generate_data_fields,
    generate_group_admins,
    generate_groups_for_services,
    generate_notifications,
    generate_profiles,
    generate_services,
    generate_youth_profiles,
)
from youths.models import YouthProfile


@pytest.mark.parametrize("times", [1, 2])
def test_generate_services(times):
    """Test services are generated and that function can be run multiple times."""
    assert Service.objects.count() == 0
    for i in range(times):
        services = generate_services()
    assert len(services) == len(ServiceType)
    assert Service.objects.count() == len(ServiceType)


@pytest.mark.parametrize("times", [1, 2])
def test_generate_group_for_service(times):
    """Test groups for services are genereted and that function can be run multiple times."""
    services = [ServiceFactory()]
    assert Group.objects.count() == 0
    for i in range(times):
        groups = generate_groups_for_services(services)
    assert len(groups) == len(services)
    assert Group.objects.count() == len(services)


@pytest.mark.parametrize("times", [1, 2])
def test_assign_permissions(times):
    available_permissions = [item[0] for item in Service._meta.permissions]
    service = ServiceFactory()
    # assign_permissions expects a Group and a Service exist with the same name.
    group = GroupFactory(name=service.service_type)
    user = UserFactory()
    user.groups.add(group)

    for permission in available_permissions:
        assert not user.has_perm(permission, service)
        assert permission not in get_group_perms(group, service)

    for i in range(times):
        assign_permissions([group])

    for permission in available_permissions:
        assert user.has_perm(permission, service)
        assert permission in get_group_perms(group, service)


@pytest.mark.parametrize("times", [1, 2])
def test_generate_notifications(times):
    """Test notifications are generated and that function can be run multiple times."""

    NotificationTemplateTranslation = apps.get_model(  # noqa: N806
        "django_ilmoitin", "NotificationTemplateTranslation"
    )

    for i in range(times):
        generate_notifications()

    assert NotificationTemplate.objects.count() == 2
    assert NotificationTemplateTranslation.objects.count() == 6


def test_creates_random_user():
    assert User.objects.count() == 1  # anonymous user exists
    user = create_user(faker=Faker())
    assert user
    assert User.objects.count() == 1
    user.save()
    assert User.objects.count() == 2


def test_creates_defined_user():
    assert User.objects.count() == 1  # anonymous user exists
    faker = Faker()
    user = create_user(username="berth_user", faker=faker)
    user.save()
    assert User.objects.count() == 2
    assert user.username == "berth_user"


def test_generates_group_admins():
    group = GroupFactory(name=ServiceType.BERTH.value)
    assert group.user_set.count() == 0
    generate_group_admins([group], faker=Faker())
    assert group.user_set.count() == 1


def test_generates_profiles():
    ServiceFactory()
    assert Profile.objects.count() == 0
    generate_profiles(k=10, faker=Faker())
    assert Profile.objects.count() == 10


def test_generates_default_amount_of_profiles():
    ServiceFactory()
    assert Profile.objects.count() == 0
    generate_profiles(faker=Faker())
    assert Profile.objects.count() == 50


def test_generates_profiles_without_any_services():
    assert Profile.objects.count() == 0
    generate_profiles(k=1, faker=Faker())
    assert Profile.objects.count() == 1


def test_generates_youth_profiles():
    generate_profiles(k=10, faker=Faker())
    assert Profile.objects.count() == 10
    assert YouthProfile.objects.count() == 0
    generate_youth_profiles(0.2, faker=Faker())
    assert YouthProfile.objects.count() == 2


def test_cant_generate_youth_profiles_without_profiles():
    assert Profile.objects.count() == 0
    assert YouthProfile.objects.count() == 0
    generate_youth_profiles(1, faker=Faker())
    assert YouthProfile.objects.count() == 0


@pytest.mark.parametrize("times", [1, 2])
def test_generate_data_fields(times):
    """Test data fields are generated and that function can be run multiple times."""
    assert AllowedDataField.objects.count() == 0
    for i in range(times):
        generate_data_fields()
    allowed_data_fields = AllowedDataField.objects.all()
    assert len(allowed_data_fields) == 5

    for value in DATA_FIELD_VALUES:
        field = allowed_data_fields.filter(field_name=value["field_name"]).first()
        assert field is not None
        for translation in value["translations"]:
            field.set_current_language(translation["code"])
            assert field.label == translation["label"]
