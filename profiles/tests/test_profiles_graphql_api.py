import uuid
from datetime import datetime, timedelta
from string import Template

import pytest
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from graphql_relay.node.node import from_global_id, to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.consts import (
    API_NOT_IMPLEMENTED_ERROR,
    PERMISSION_DENIED_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
    TOKEN_EXPIRED_ERROR,
)
from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_almost_equal, assert_match_error_code
from open_city_profile.tests.factories import GroupFactory
from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import (
    _default_temporary_read_access_token_validity_duration,
    Profile,
    TemporaryReadAccessToken,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory
from subscriptions.models import Subscription
from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)

from .conftest import ProfileWithVerifiedPersonalInformationTestBase
from .factories import (
    AddressFactory,
    ClaimTokenFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    TemporaryReadAccessTokenFactory,
)


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client, service_factory):
    service_factory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_admin_user_can_query_berth_profiles(
    rf, superuser_gql_client, profile, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                        lastName
                        nickname
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {
            "edges": [
                {
                    "node": {
                        "firstName": profile.first_name,
                        "lastName": profile.last_name,
                        "nickname": profile.nickname,
                    }
                }
            ]
        }
    }
    executed = superuser_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_with_group_access_can_query_berth_profiles(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_profiles_by_profile_ids(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getProfiles($serviceType: ServiceType!, $ids: [UUID!]!){
            profiles(serviceType: $serviceType, id: $ids) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "ids": [str(profile_2.id), str(profile_1.id), str(uuid.uuid4())],
        },
        context=request,
    )
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_first_name(
    rf, user_gql_client, group, service
):
    profile_1, profile_2 = ProfileFactory.create_batch(2)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $firstName: String){
            profiles(serviceType: $serviceType, firstName: $firstName) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 2}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "firstName": profile_2.first_name,
        },
        context=request,
    )
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_sort_berth_profiles(rf, user_gql_client, group, service):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        query getBerthProfiles {
            profiles(serviceType: ${service_type}, orderBy: "-firstName") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "order_by",
    [
        "primaryAddress",
        "primaryCity",
        "primaryPostalCode",
        "primaryCountryCode",
        "primaryEmail",
    ],
)
def test_staff_user_can_sort_berth_profiles_by_custom_fields(
    rf, user_gql_client, group, service, order_by
):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    AddressFactory(
        profile=profile_1,
        city="Akaa",
        address="Autotie 1",
        postal_code="00100",
        country_code="FI",
        primary=True,
    ),
    AddressFactory(
        profile=profile_2,
        city="Ypäjä",
        address="Yrjönkatu 99",
        postal_code="99999",
        country_code="SE",
        primary=True,
    ),
    EmailFactory(profile=profile_1, email="adam.tester@example.com", primary=True,),
    EmailFactory(profile=profile_2, email="bryan.tester@example.com", primary=True,),
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        query getBerthProfiles {
            profiles(serviceType: ${service_type}, orderBy: \"${order_by}\") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name, order_by=order_by)
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Adam"}}, {"node": {"firstName": "Bryan"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = t.substitute(service_type=ServiceType.BERTH.name, order_by=f"-{order_by}")
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_emails(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    EmailFactory(
        profile=profile_1, primary=True, email_type=EmailType.PERSONAL, verified=True
    )
    email = EmailFactory(profile=profile_2, primary=False, email_type=EmailType.WORK)
    EmailFactory(profile=profile_3, primary=False, email_type=EmailType.OTHER)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by email

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $email: String){
            profiles(serviceType: $serviceType, emails_Email: $email) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "email": email.email},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by email_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $emailType: String){
            profiles(serviceType: $serviceType, emails_EmailType: $emailType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "emailType": email.email_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, emails_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by verified

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $verified: Boolean){
            profiles(serviceType: $serviceType, emails_Verified: $verified) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "verified": True},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_phones(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    PhoneFactory(profile=profile_1, primary=True, phone_type=PhoneType.HOME)
    phone = PhoneFactory(profile=profile_2, primary=False, phone_type=PhoneType.WORK)
    PhoneFactory(profile=profile_3, primary=False, phone_type=PhoneType.MOBILE)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by phone

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $phone: String){
            profiles(serviceType: $serviceType, phones_Phone: $phone) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "phone": phone.phone},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by phone_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $phoneType: String){
            profiles(serviceType: $serviceType, phones_PhoneType: $phoneType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "phoneType": phone.phone_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, phones_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_addresses(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    AddressFactory(
        profile=profile_1,
        postal_code="00100",
        city="Helsinki",
        country_code="FI",
        primary=True,
        address_type=AddressType.HOME,
    )
    address = AddressFactory(
        profile=profile_2,
        postal_code="00100",
        city="Espoo",
        country_code="FI",
        primary=False,
        address_type=AddressType.WORK,
    )
    AddressFactory(
        profile=profile_3,
        postal_code="00200",
        city="Stockholm",
        country_code="SE",
        primary=False,
        address_type=AddressType.OTHER,
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by address

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $address: String){
            profiles(serviceType: $serviceType, addresses_Address: $address) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "address": address.address},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by postal_code

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $postalCode: String){
            profiles(serviceType: $serviceType, addresses_PostalCode: $postalCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "postalCode": address.postal_code,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by city

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $city: String){
            profiles(serviceType: $serviceType, addresses_City: $city) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "city": address.city},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by country code

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $countryCode: String){
            profiles(serviceType: $serviceType, addresses_CountryCode: $countryCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "countryCode": address.country_code,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by address_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $addressType: String){
            profiles(serviceType: $serviceType, addresses_AddressType: $addressType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "addressType": address.address_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, addresses_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_subscriptions_and_postal_code(
    rf, user_gql_client, group, service
):
    def generate_expected_data(profiles):
        return {
            "profiles": {
                "edges": [
                    {
                        "node": {
                            "emails": {
                                "edges": [
                                    {"node": {"email": profile.emails.first().email}}
                                ]
                            },
                            "phones": {
                                "edges": [
                                    {"node": {"phone": profile.phones.first().phone}}
                                ]
                            },
                        }
                    }
                    for profile in profiles
                ]
            }
        }

    profile_1, profile_2, profile_3, profile_4 = ProfileFactory.create_batch(4)
    PhoneFactory(profile=profile_1, phone="0401234561", primary=True)
    PhoneFactory(profile=profile_2, phone="0401234562", primary=True)
    PhoneFactory(profile=profile_3, phone="0401234563", primary=True)
    PhoneFactory(profile=profile_4, phone="0401234564", primary=True)

    EmailFactory(profile=profile_1, email="first@example.com", primary=True)
    EmailFactory(profile=profile_2, email="second@example.com", primary=True)
    EmailFactory(profile=profile_3, email="third@example.com", primary=True)
    EmailFactory(profile=profile_4, email="fourth@example.com", primary=True)

    AddressFactory(profile=profile_1, primary=True, postal_code="00100")
    AddressFactory(profile=profile_2, postal_code="00100")
    AddressFactory(profile=profile_3, postal_code="00100")
    AddressFactory(profile=profile_4, postal_code="00200")

    cat = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-1")
    type_1 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-1")
    type_2 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-2")

    Subscription.objects.create(
        profile=profile_1, subscription_type=type_1, enabled=True
    )
    Subscription.objects.create(
        profile=profile_1, subscription_type=type_2, enabled=True
    )

    Subscription.objects.create(
        profile=profile_2, subscription_type=type_1, enabled=True
    )
    Subscription.objects.create(
        profile=profile_2, subscription_type=type_2, enabled=False
    )

    Subscription.objects.create(
        profile=profile_3, subscription_type=type_1, enabled=True
    )

    Subscription.objects.create(
        profile=profile_4, subscription_type=type_2, enabled=True
    )

    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    ServiceConnectionFactory(profile=profile_4, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $subscriptionType: String, $postalCode: String){
            profiles(
                serviceType: $serviceType,
                enabledSubscriptions: $subscriptionType,
                addresses_PostalCode: $postalCode
            ) {
                edges {
                    node {
                        emails {
                            edges {
                                node {
                                    email
                                }
                            }
                        }
                        phones {
                            edges {
                                node {
                                    phone
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    # test for type 1 + postal code 00100

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "subscriptionType": type_1.code,
            "postalCode": "00100",
        },
        context=request,
    )
    assert dict(executed["data"]) == generate_expected_data(
        [profile_1, profile_2, profile_3]
    )

    # test for type 2 + postal code 00100

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "subscriptionType": type_2.code,
            "postalCode": "00100",
        },
        context=request,
    )
    assert dict(executed["data"]) == generate_expected_data([profile_1])


def test_staff_user_can_paginate_berth_profiles(rf, user_gql_client, group, service):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles {
            profiles(serviceType: BERTH, orderBy: "firstName", first: 1) {
                pageInfo {
                    endCursor
                }
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {"edges": [{"node": {"firstName": "Adam"}}]}
    executed = user_gql_client.execute(query, context=request)
    assert "data" in executed
    assert executed["data"]["profiles"]["edges"] == expected_data["edges"]
    assert "pageInfo" in executed["data"]["profiles"]
    assert "endCursor" in executed["data"]["profiles"]["pageInfo"]

    end_cursor = executed["data"]["profiles"]["pageInfo"]["endCursor"]

    query = """
        query getBerthProfiles($endCursor: String){
            profiles(serviceType: BERTH, first: 1, after: $endCursor) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected_data = {"edges": [{"node": {"firstName": "Bryan"}}]}
    executed = user_gql_client.execute(
        query, variables={"endCursor": end_cursor}, context=request
    )
    assert "data" in executed
    assert executed["data"]["profiles"] == expected_data


def test_staff_user_with_group_access_can_query_only_profiles_he_has_access_to(
    rf, user_gql_client, group, service_factory
):
    profile_berth = ProfileFactory()
    profile_youth = ProfileFactory()
    service_berth = service_factory(service_type=ServiceType.BERTH)
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile_berth, service=service_berth)
    ServiceConnectionFactory(profile=profile_youth, service=service_youth)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_berth)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile_berth.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.YOUTH_MEMBERSHIP.name)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_can_create_a_profile(
    rf, user_gql_client, email_data, phone_data, address_data, group, service
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        lastName: \"${last_name}\",
                        addEmails: [{
                            emailType: ${email_type},
                            email: \"${email}\",
                            primary: true,
                        }],
                        addPhones: [{
                            phoneType: ${phone_type},
                            phone: \"${phone}\",
                            primary: true
                        }]
                    }
                }
            ) {
                profile {
                    firstName
                    lastName
                    phones {
                        edges {
                            node {
                                phoneType
                                phone
                                primary
                            }
                        }
                    }
                    emails {
                        edges {
                            node {
                                emailType
                                email
                                primary
                            }
                        }
                    }
                    serviceConnections {
                        edges {
                            node {
                                service {
                                    type
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.BERTH.name,
        first_name="John",
        last_name="Doe",
        phone_type=phone_data["phone_type"],
        phone=phone_data["phone"],
        email_type=email_data["email_type"],
        email=email_data["email"],
    )
    expected_data = {
        "createProfile": {
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "phones": {
                    "edges": [
                        {
                            "node": {
                                "phoneType": phone_data["phone_type"],
                                "phone": phone_data["phone"],
                                "primary": True,
                            }
                        }
                    ]
                },
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "emailType": email_data["email_type"],
                                "email": email_data["email"],
                                "primary": True,
                            }
                        }
                    ]
                },
                "serviceConnections": {
                    "edges": [{"node": {"service": {"type": ServiceType.BERTH.name}}}]
                },
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_cannot_create_a_profile_using_create_profile_mutation(
    rf, user_gql_client, service_factory
):
    service_factory()
    user = user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                    }
                }
            ) {
                profile {
                    firstName
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name, first_name="John")
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_cannot_create_a_profile_without_service_access(
    rf, user_gql_client, service_factory
):
    service_factory(service_type=ServiceType.BERTH)
    service = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory(name="youth_membership")
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                    }
                }
            ) {
                profile {
                    firstName
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name, first_name="John")
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_with_sensitive_data_service_accesss_can_create_a_profile_with_sensitive_data(
    rf, user_gql_client, email_data, group, service
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_manage_sensitivedata", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        addEmails: [{
                            email: \"${email}\",
                            emailType: ${email_type},
                            primary: true
                        }],
                        sensitivedata: {
                            ssn: \"${ssn}\"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.BERTH.name,
        first_name="John",
        ssn="121282-123E",
        email=email_data["email"],
        email_type=email_data["email_type"],
    )

    expected_data = {
        "createProfile": {
            "profile": {"firstName": "John", "sensitivedata": {"ssn": "121282-123E"}}
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_cannot_create_a_profile_with_sensitive_data_without_sensitive_data_service_access(
    rf, user_gql_client, service_factory
):
    service_berth = service_factory(service_type=ServiceType.BERTH)
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group_berth = GroupFactory(name=ServiceType.BERTH.value)
    group_youth = GroupFactory(name="youth_membership")
    user = user_gql_client.user
    user.groups.add(group_berth)
    user.groups.add(group_youth)
    assign_perm("can_manage_profiles", group_berth, service_berth)
    assign_perm("can_manage_sensitivedata", group_youth, service_youth)
    assign_perm("can_view_sensitivedata", group_youth, service_youth)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        sensitivedata: {
                            ssn: \"${ssn}\"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.BERTH.name, first_name="John", ssn="121282-123E"
    )

    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


@pytest.mark.parametrize("service__service_type", [ServiceType.YOUTH_MEMBERSHIP])
def test_staff_user_can_update_a_profile(rf, user_gql_client, group, service):
    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    phone = PhoneFactory(profile=profile)
    address = AddressFactory(profile=profile)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    assign_perm("can_manage_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user

    data = {
        "first_name": "John",
        "email": {
            "email": "another@example.com",
            "email_type": EmailType.WORK.name,
            "primary": False,
        },
        "phone": "0407654321",
        "school_class": "5F",
        "ssn": "010199-1234",
    }

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        id: \"${id}\",
                        firstName: \"${first_name}\",
                        addEmails: [{
                            email: \"${email}\"
                            emailType: ${email_type}
                            primary: ${primary}
                        }],
                        updatePhones: [{
                            id: \"${phone_id}\",
                            phone: \"${phone}\",
                        }],
                        removeAddresses: [\"${address_id}\"],
                        sensitivedata: {
                            ssn: \"${ssn}\"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    emails {
                        edges {
                            node {
                                email
                            }
                        }
                    }
                    phones {
                        edges {
                            node {
                                phone
                            }
                        }
                    }
                    addresses {
                        edges {
                            node {
                                address
                            }
                        }
                    }
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        id=to_global_id("ProfileNode", profile.pk),
        first_name=data["first_name"],
        phone_id=to_global_id("PhoneNode", phone.pk),
        email=data["email"]["email"],
        email_type=data["email"]["email_type"],
        primary=str(data["email"]["primary"]).lower(),
        phone=data["phone"],
        address_id=to_global_id(type="AddressNode", id=address.pk),
        ssn=data["ssn"],
    )
    expected_data = {
        "updateProfile": {
            "profile": {
                "firstName": data["first_name"],
                "emails": {
                    "edges": [
                        {"node": {"email": profile.emails.first().email}},
                        {"node": {"email": data["email"]["email"]}},
                    ]
                },
                "phones": {"edges": [{"node": {"phone": data["phone"]}}]},
                "addresses": {"edges": []},
                "sensitivedata": {"ssn": data["ssn"]},
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


@pytest.mark.parametrize("service__service_type", [ServiceType.YOUTH_MEMBERSHIP])
def test_staff_user_cannot_update_profile_sensitive_data_without_correct_permission(
    rf, user_gql_client, group, service
):
    """A staff user without can_manage_sensitivedata permission cannot update sensitive data."""
    profile = ProfileWithPrimaryEmailFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)

    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        id: \"${id}\",
                        sensitivedata: {
                            ssn: \"${ssn}\"
                        }
                    }
                }
            ) {
                profile {
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        id=to_global_id("ProfileNode", profile.pk),
        ssn="010199-1234",
    )
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_normal_user_cannot_update_a_profile_using_update_profile_mutation(
    rf, user_gql_client, service_factory
):
    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        id: \"${id}\",
                        firstName: \"${first_name}\",
                    }
                }
            ) {
                profile {
                    firstName
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        id=to_global_id("ProfileNode", profile.pk),
        first_name="John",
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )
    assert Profile.objects.get(pk=profile.pk).first_name == profile.first_name


class TestProfileWithVerifiedPersonalInformationCreation(
    ProfileWithVerifiedPersonalInformationTestBase
):
    @staticmethod
    def execute_mutation(input_data, rf, gql_client):
        user = gql_client.user

        assign_perm("profiles.manage_verified_personal_information", user)

        request = rf.post("/graphql")
        request.user = user

        query = """
            mutation createOrUpdateProfileWithVerifiedPersonalInformation(
                $input: CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput!
            ) {
                prof: createOrUpdateProfileWithVerifiedPersonalInformation(
                    input: $input,
                ) {
                    profile {
                        id,
                    }
                }
            }
        """

        return gql_client.execute(
            query, variables={"input": input_data}, context=request
        )

    @staticmethod
    def execute_successful_mutation(input_data, rf, gql_client):
        executed = TestProfileWithVerifiedPersonalInformationCreation.execute_mutation(
            input_data, rf, gql_client
        )

        global_profile_id = executed["data"]["prof"]["profile"]["id"]
        profile_id = uuid.UUID(from_global_id(global_profile_id)[1])

        return Profile.objects.get(pk=profile_id)

    @staticmethod
    def execute_successful_profile_creation_test(user_id, rf, gql_client):
        input_data = {
            "userId": str(user_id),
            "profile": {
                "verifiedPersonalInformation": {
                    "firstName": "John",
                    "lastName": "Smith",
                    "givenName": "Johnny",
                    "nationalIdentificationNumber": "220202A1234",
                    "email": "john.smith@domain.example",
                    "municipalityOfResidence": "Helsinki",
                    "municipalityOfResidenceNumber": "091",
                    "permanentAddress": {
                        "streetAddress": "Permanent Street 1",
                        "postalCode": "12345",
                        "postOffice": "Permanent City",
                    },
                    "temporaryAddress": {
                        "streetAddress": "Temporary Street 2",
                        "postalCode": "98765",
                        "postOffice": "Temporary City",
                    },
                    "permanentForeignAddress": {
                        "streetAddress": "〒100-8994",
                        "additionalAddress": "東京都中央区八重洲1-5-3",
                        "countryCode": "JP",
                    },
                },
            },
        }

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, gql_client
        )

        assert profile.user.uuid == user_id
        verified_personal_information = profile.verified_personal_information
        assert verified_personal_information.first_name == "John"
        assert verified_personal_information.last_name == "Smith"
        assert verified_personal_information.given_name == "Johnny"
        assert (
            verified_personal_information.national_identification_number
            == "220202A1234"
        )
        assert verified_personal_information.email == "john.smith@domain.example"
        assert verified_personal_information.municipality_of_residence == "Helsinki"
        assert verified_personal_information.municipality_of_residence_number == "091"
        permanent_address = verified_personal_information.permanent_address
        assert permanent_address.street_address == "Permanent Street 1"
        assert permanent_address.postal_code == "12345"
        assert permanent_address.post_office == "Permanent City"
        temporary_address = verified_personal_information.temporary_address
        assert temporary_address.street_address == "Temporary Street 2"
        assert temporary_address.postal_code == "98765"
        assert temporary_address.post_office == "Temporary City"
        permanent_foreign_address = (
            verified_personal_information.permanent_foreign_address
        )
        assert permanent_foreign_address.street_address == "〒100-8994"
        assert permanent_foreign_address.additional_address == "東京都中央区八重洲1-5-3"
        assert permanent_foreign_address.country_code == "JP"

    def test_profile_with_verified_personal_information_can_be_created(
        self, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(uuid.uuid1(), rf, user_gql_client)

    def test_manage_verified_personal_information_permission_is_needed(
        self, rf, user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = user_gql_client.user

        query = """
        mutation {
            createOrUpdateProfileWithVerifiedPersonalInformation(
                input: {
                    userId: "03117666-117D-4F6B-80B1-A3A92B389711",
                    profile: {
                        verifiedPersonalInformation: {
                        }
                    }
                }
            ) {
                profile {
                    id,
                }
            }
        }
        """

        executed = user_gql_client.execute(query, context=request)
        assert executed["errors"][0]["extensions"]["code"] == "PERMISSION_DENIED_ERROR"

    def test_existing_user_is_used(self, user, rf, user_gql_client):
        self.execute_successful_profile_creation_test(user.uuid, rf, user_gql_client)

    def test_existing_profile_without_verified_personal_information_is_updated(
        self, profile, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(
            profile.user.uuid, rf, user_gql_client
        )

    def test_existing_profile_with_verified_personal_information_is_updated(
        self, profile_with_verified_personal_information, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(
            profile_with_verified_personal_information.user.uuid, rf, user_gql_client,
        )

    def test_all_basic_fields_can_be_set_to_null(self, rf, user_gql_client):
        input_data = {
            "userId": "03117666-117D-4F6B-80B1-A3A92B389711",
            "profile": {
                "verifiedPersonalInformation": {
                    "firstName": None,
                    "lastName": None,
                    "givenName": None,
                    "nationalIdentificationNumber": None,
                    "email": None,
                    "municipalityOfResidence": None,
                    "municipalityOfResidenceNumber": None,
                },
            },
        }

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        verified_personal_information = profile.verified_personal_information
        assert verified_personal_information.first_name == ""
        assert verified_personal_information.last_name == ""
        assert verified_personal_information.given_name == ""
        assert verified_personal_information.national_identification_number == ""
        assert verified_personal_information.email == ""
        assert verified_personal_information.municipality_of_residence == ""
        assert verified_personal_information.municipality_of_residence_number == ""

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    @pytest.mark.parametrize("address_field_index_to_nullify", [0, 1, 2])
    def test_address_fields_can_be_set_to_null(
        self,
        profile_with_verified_personal_information,
        address_type,
        address_field_index_to_nullify,
        rf,
        user_gql_client,
    ):
        address_field_names = self.ADDRESS_FIELD_NAMES[address_type]
        field_to_nullify = address_field_names[address_field_index_to_nullify]

        existing_address = getattr(
            profile_with_verified_personal_information.verified_personal_information,
            address_type,
        )

        user_id = profile_with_verified_personal_information.user.uuid

        address_data = {to_graphql_name(field_to_nullify): None}

        input_data = {
            "userId": str(user_id),
            "profile": {
                "verifiedPersonalInformation": {
                    to_graphql_name(address_type): address_data
                },
            },
        }

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        address = getattr(profile.verified_personal_information, address_type)

        for field_name in address_field_names:
            if field_name == field_to_nullify:
                assert getattr(address, field_name) == ""
            else:
                assert getattr(address, field_name) == getattr(
                    existing_address, field_name
                )

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    def test_do_not_touch_an_address_if_it_is_not_included_in_the_mutation(
        self,
        profile_with_verified_personal_information,
        address_type,
        rf,
        user_gql_client,
    ):
        existing_address = getattr(
            profile_with_verified_personal_information.verified_personal_information,
            address_type,
        )

        user_id = profile_with_verified_personal_information.user.uuid

        input_data = {
            "userId": str(user_id),
            "profile": {"verifiedPersonalInformation": {}},
        }

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        verified_personal_information = profile.verified_personal_information
        address = getattr(verified_personal_information, address_type)

        for field_name in self.ADDRESS_FIELD_NAMES[address_type]:
            assert getattr(address, field_name) == getattr(existing_address, field_name)

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    def test_delete_an_address_if_it_no_longer_has_any_data(
        self,
        profile_with_verified_personal_information,
        address_type,
        rf,
        user_gql_client,
    ):
        user_id = profile_with_verified_personal_information.user.uuid

        address_fields = {}
        for name in self.ADDRESS_FIELD_NAMES[address_type]:
            address_fields[to_graphql_name(name)] = ""

        input_data = {
            "userId": str(user_id),
            "profile": {
                "verifiedPersonalInformation": {
                    to_graphql_name(address_type): address_fields
                },
            },
        }

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, user_gql_client
        )

        assert not hasattr(profile.verified_personal_information, address_type)

    @staticmethod
    def service_input_data(user_id, service_client_id):
        user_id = str(user_id)
        return {
            "userId": user_id,
            "serviceClientId": service_client_id,
            "profile": {"verifiedPersonalInformation": {"firstName": "John"}},
        }

    @staticmethod
    def execute_service_connection_test(
        user_id, service_in_mutation, expected_service_connections, rf, gql_client
    ):
        input_data = TestProfileWithVerifiedPersonalInformationCreation.service_input_data(
            user_id, service_in_mutation.client_ids.first().client_id
        )

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, gql_client
        )

        connected_services = profile.service_connections.all()

        assert connected_services.count() == len(expected_service_connections)
        for service in expected_service_connections:
            connection = connected_services.get(service=service)
            assert connection.service == service
            assert connection.enabled

    def test_giving_non_existing_service_client_id_results_in_object_does_not_exist_error(
        self, rf, user_gql_client
    ):
        input_data = self.service_input_data(uuid.uuid1(), "not_existing")

        executed = self.execute_mutation(input_data, rf, user_gql_client)

        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")

    def test_add_new_service_connections(
        self, service_factory, service_client_id_factory, rf, user_gql_client
    ):
        user_id = uuid.uuid1()
        service1 = service_factory(service_type=ServiceType.BERTH)
        service2 = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
        service_client_id_factory(service=service1)
        service_client_id_factory(service=service2)

        self.execute_service_connection_test(
            user_id, service1, [service1], rf, user_gql_client
        )

        self.execute_service_connection_test(
            user_id, service2, [service1, service2], rf, user_gql_client
        )

    def test_adding_existing_connection_again_does_nothing(
        self,
        profile,
        service,
        service_connection_factory,
        service_client_id_factory,
        rf,
        user_gql_client,
    ):
        service_client_id_factory(service=service)
        service_connection_factory(profile=profile, service=service, enabled=True)

        self.execute_service_connection_test(
            profile.user.uuid, service, [service], rf, user_gql_client
        )

    def test_enable_existing_disabled_service_connection(
        self,
        profile,
        service,
        service_connection_factory,
        service_client_id_factory,
        rf,
        user_gql_client,
    ):
        service_client_id_factory(service=service)
        service_connection_factory(profile=profile, service=service, enabled=False)

        self.execute_service_connection_test(
            profile.user.uuid, service, [service], rf, user_gql_client
        )

    @staticmethod
    def execute_mutation_with_invalid_input(rf, gql_client):
        input_data = {
            "userId": "03117666-117D-4F6B-80B1-A3A92B389711",
            "profile": {
                "verifiedPersonalInformation": {
                    "permanentForeignAddress": {"countryCode": "France"}
                }
            },
        }

        return TestProfileWithVerifiedPersonalInformationCreation.execute_mutation(
            input_data, rf, gql_client
        )

    def test_invalid_input_causes_a_validation_error(self, rf, user_gql_client):
        executed = self.execute_mutation_with_invalid_input(rf, user_gql_client)
        assert executed["errors"][0]["extensions"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.django_db(transaction=True)
    def test_database_stays_unmodified_when_mutation_is_not_completed(
        self, rf, user_gql_client
    ):
        self.execute_mutation_with_invalid_input(rf, user_gql_client)

        assert Profile.objects.count() == 0
        assert VerifiedPersonalInformation.objects.count() == 0
        assert VerifiedPersonalInformationPermanentAddress.objects.count() == 0
        assert VerifiedPersonalInformationTemporaryAddress.objects.count() == 0
        assert VerifiedPersonalInformationPermanentForeignAddress.objects.count() == 0


def test_profile_node_exposes_key_for_federation_gateway(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        'type ProfileNode implements Node  @key(fields: "id")'
        in executed["data"]["_service"]["sdl"]
    )


def test_profile_connection_schema_matches_federated_schema(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        "type ProfileNodeConnection {   pageInfo: PageInfo!   "
        "edges: [ProfileNodeEdge]!   count: Int!   totalCount: Int! }"
        in executed["data"]["_service"]["sdl"]
    )


def test_can_query_claimable_profile_with_token(rf, user_gql_client):
    profile = ProfileFactory(user=None, first_name="John", last_name="Doe")
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
                firstName
                lastName
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    expected_data = {
        "claimableProfile": {
            "id": to_global_id(type="ProfileNode", id=profile.id),
            "firstName": profile.first_name,
            "lastName": profile.last_name,
        }
    }
    executed = user_gql_client.execute(query, context=request)

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_cannot_query_claimable_profile_with_user_already_attached(
    rf, user_gql_client, profile
):
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed


def test_cannot_query_claimable_profile_with_expired_token(rf, user_gql_client):
    profile = ProfileFactory(user=None)
    claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_user_can_claim_claimable_profile_without_existing_profile(rf, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    expected_data = {
        "claimProfile": {
            "profile": {
                "id": to_global_id(type="ProfileNode", id=profile.id),
                "firstName": "Joe",
                "nickname": "Joey",
                "lastName": profile.last_name,
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
    profile.refresh_from_db()
    assert profile.user == user_gql_client.user
    assert profile.claim_tokens.count() == 0


def test_user_cannot_claim_claimable_profile_if_token_expired(rf, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    expired_claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=expired_claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_user_cannot_claim_claimable_profile_with_existing_profile(rf, user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    profile_to_claim = ProfileFactory(user=None, first_name="John", last_name="Doe")
    expired_claim_token = ClaimTokenFactory(profile=profile_to_claim)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=expired_claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == API_NOT_IMPLEMENTED_ERROR


class TemporaryProfileReadAccessTokenTestBase:
    def create_expired_token(self, profile):
        over_default_validity_duration = _default_temporary_read_access_token_validity_duration() + timedelta(
            seconds=1
        )
        expired_token_creation_time = timezone.now() - over_default_validity_duration
        token = TemporaryReadAccessTokenFactory(
            profile=profile, created_at=expired_token_creation_time
        )
        return token


class TestTemporaryProfileReadAccessTokenCreation(
    TemporaryProfileReadAccessTokenTestBase
):
    query = """
        mutation {
            createMyProfileTemporaryReadAccessToken(input: { }) {
                temporaryReadAccessToken {
                    token
                    expiresAt
                }
            }
        }
    """

    def test_normal_user_can_create_temporary_read_access_token_for_profile(
        self, rf, user_gql_client
    ):
        ProfileFactory(user=user_gql_client.user)
        request = rf.post("/graphql")
        request.user = user_gql_client.user

        executed = user_gql_client.execute(self.query, context=request)

        token_data = executed["data"]["createMyProfileTemporaryReadAccessToken"][
            "temporaryReadAccessToken"
        ]

        # Check that an UUID can be parsed from the token
        uuid.UUID(token_data["token"])

        actual_expiration_time = datetime.fromisoformat(token_data["expiresAt"])
        expected_expiration_time = timezone.now() + timedelta(days=2)
        assert_almost_equal(
            actual_expiration_time, expected_expiration_time, timedelta(seconds=1)
        )

    def test_anonymous_user_cannot_create_any_temporary_read_access_token_for_profile(
        self, rf, anon_user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(self.query, context=request)

        assert executed["errors"][0]["extensions"]["code"] == PERMISSION_DENIED_ERROR

    def test_other_valid_tokens_are_deleted_when_a_new_token_is_created(
        self, rf, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        request = rf.post("/graphql")
        request.user = user_gql_client.user

        valid_token1 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token2 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token_for_another_profile = TemporaryReadAccessTokenFactory()
        expired_token = self.create_expired_token(profile)

        executed = user_gql_client.execute(self.query, context=request)
        token_data = executed["data"]["createMyProfileTemporaryReadAccessToken"][
            "temporaryReadAccessToken"
        ]
        new_token_uuid = uuid.UUID(token_data["token"])

        def token_exists(token):
            token = token if isinstance(token, uuid.UUID) else token.token
            return TemporaryReadAccessToken.objects.filter(token=token).exists()

        assert not token_exists(valid_token1)
        assert not token_exists(valid_token2)
        assert token_exists(expired_token)
        assert token_exists(new_token_uuid)
        assert token_exists(valid_token_for_another_profile)


class TestTemporaryProfileReadAccessToken(TemporaryProfileReadAccessTokenTestBase):
    def query(self, token):
        return Template(
            """
            {
                profileWithAccessToken(token: "${token}") {
                    firstName
                    lastName
                }
            }
        """
        ).substitute(token=token)

    def test_anonymous_user_can_retrieve_a_profile_with_temporary_read_access_token(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        token = TemporaryReadAccessTokenFactory(profile=profile)

        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(token.token), context=request
        )

        assert "errors" not in executed
        actual_profile = executed["data"]["profileWithAccessToken"]
        assert actual_profile == {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
        }

    def test_only_a_limited_set_of_fields_is_returned_from_the_profile(
        self, gql_schema
    ):
        query_type = gql_schema.get_query_type()
        operation = query_type.fields["profileWithAccessToken"]
        return_type = operation.type
        return_fields = return_type.fields.keys()
        assert set(return_fields) == set(
            [
                "firstName",
                "lastName",
                "nickname",
                "image",
                "language",
                "id",
                "primaryEmail",
                "primaryPhone",
                "primaryAddress",
                "emails",
                "phones",
                "addresses",
                "contactMethod",
            ]
        )

    def test_using_non_existing_token_reports_profile_not_found_error(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(uuid.uuid4()), context=request
        )

        assert (
            executed["errors"][0]["extensions"]["code"] == PROFILE_DOES_NOT_EXIST_ERROR
        )

    def test_using_an_expired_token_reports_token_expired_error(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        token = self.create_expired_token(profile)

        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(token.token), context=request
        )

        assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR
