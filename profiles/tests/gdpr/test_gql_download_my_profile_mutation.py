import json
from string import Template

import pytest
from django.utils.translation import gettext as _

from open_city_profile.consts import MISSING_GDPR_API_TOKEN_ERROR
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.tests.factories import (
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    VerifiedPersonalInformationFactory,
)
from services.tests.factories import ServiceConnectionFactory

AUTHORIZATION_CODE = "code123"

DOWNLOAD_MY_PROFILE_MUTATION = Template(
    """
    {
        downloadMyProfile(authorizationCode: "${auth_code}")
    }
"""
).substitute(auth_code=AUTHORIZATION_CODE)

SERVICE_DATA_1 = {
    "key": "SERVICE-1",
    "children": [{"key": "CUSTOMERID", "value": "123"}],
}

SERVICE_DATA_2 = {
    "key": "SERVICE-2",
    "children": [{"key": "STATUS", "value": "PENDING"}],
}


def test_user_can_download_profile(user_gql_client, profile_service):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(
        profile=profile, service=profile_service
    )
    service_connection_created_at = service_connection.created_at.date().isoformat()

    primary_email = profile.emails.first()

    executed = user_gql_client.execute(
        DOWNLOAD_MY_PROFILE_MUTATION, service=profile_service
    )

    expected_json = json.dumps(
        {
            "key": "DATA",
            "children": [
                {
                    "key": "PROFILE",
                    "children": [
                        {"key": "FIRST_NAME", "value": profile.first_name},
                        {"key": "LAST_NAME", "value": profile.last_name},
                        {"key": "NICKNAME", "value": profile.nickname},
                        {"key": "LANGUAGE", "value": profile.language},
                        {"key": "CONTACT_METHOD", "value": profile.contact_method},
                        {
                            "key": "EMAILS",
                            "children": [
                                {
                                    "key": "EMAIL",
                                    "children": [
                                        {
                                            "key": "PRIMARY",
                                            "value": primary_email.primary,
                                        },
                                        {
                                            "key": "EMAIL_TYPE",
                                            "value": primary_email.email_type.name,
                                        },
                                        {"key": "EMAIL", "value": primary_email.email},
                                    ],
                                }
                            ],
                        },
                        {"key": "PHONES", "children": []},
                        {"key": "ADDRESSES", "children": []},
                        {
                            "key": "SERVICE_CONNECTIONS",
                            "children": [
                                {
                                    "key": "SERVICECONNECTION",
                                    "children": [
                                        {
                                            "key": "SERVICE",
                                            "value": profile_service.name,
                                        },
                                        {
                                            "key": "CREATED_AT",
                                            "value": service_connection_created_at,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ],
        }
    )
    assert executed["data"]["downloadMyProfile"] == expected_json, executed


def test_user_can_not_download_profile_without_service_connection(
    service_1, user_gql_client
):
    ProfileFactory(user=user_gql_client.user)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION, service=service_1)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
    assert executed["data"]["downloadMyProfile"] is None


def download_verified_personal_information_with_loa(loa, user_gql_client, service):
    VerifiedPersonalInformationFactory(profile__user=user_gql_client.user)

    token_payload = {
        "loa": loa,
    }
    executed = user_gql_client.execute(
        DOWNLOAD_MY_PROFILE_MUTATION, service=service, auth_token_payload=token_payload
    )

    full_dump = json.loads(executed["data"]["downloadMyProfile"])
    profile_dump = next(
        child for child in full_dump["children"] if child["key"] == "PROFILE"
    )
    vpi_dump = next(
        child
        for child in profile_dump["children"]
        if child["key"] == "VERIFIEDPERSONALINFORMATION"
    )

    return vpi_dump


@pytest.mark.parametrize("loa", ["substantial", "high"])
def test_verified_personal_information_is_included_in_the_downloaded_profile_when_loa_is_high_enough(
    loa, user_gql_client, profile_service
):
    vpi_dump = download_verified_personal_information_with_loa(
        loa, user_gql_client, profile_service
    )

    assert "error" not in vpi_dump
    assert len(vpi_dump["children"]) > 0


@pytest.mark.parametrize("loa", [None, "foo", "low"])
def test_verified_personal_information_is_replaced_with_an_error_when_loa_is_not_high_enough(
    loa, user_gql_client, profile_service
):
    vpi_dump = download_verified_personal_information_with_loa(
        loa, user_gql_client, profile_service
    )

    assert vpi_dump == {
        "key": "VERIFIEDPERSONALINFORMATION",
        "error": _("No permission to read verified personal information."),
    }


def test_downloading_non_existent_profile_doesnt_return_errors(user_gql_client):
    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert "errors" not in executed


def test_user_can_download_profile_with_connected_services_using_correct_api_tokens(
    user_gql_client,
    service_1,
    service_2,
    gdpr_api_tokens,
    api_token_1,
    api_token_2,
    mocker,
    requests_mock,
):
    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )

    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    service_1_gdpr_url = service_connection_1.get_gdpr_url()
    service_2_gdpr_url = service_connection_2.get_gdpr_url()

    def get_response(request, context):
        if (
            request.url == service_1_gdpr_url
            and request.headers["authorization"] == f"Bearer {api_token_1}"
        ):
            return SERVICE_DATA_1

        if (
            request.url == service_2_gdpr_url
            and request.headers["authorization"] == f"Bearer {api_token_2}"
        ):
            return SERVICE_DATA_2

        raise RuntimeError("Unexpected GDPR API call")

    requests_mock.get(service_1_gdpr_url, json=get_response)
    requests_mock.get(service_2_gdpr_url, json=get_response)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    mocked_token_exchange.assert_called_once()
    assert mocked_token_exchange.call_args == ((AUTHORIZATION_CODE,),)
    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert SERVICE_DATA_1 in response_data
    assert SERVICE_DATA_2 in response_data


def test_empty_data_from_connected_service_is_not_included_in_response(
    user_gql_client, service_1, gdpr_api_tokens, mocker, requests_mock
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )

    profile = ProfileFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(profile=profile, service=service_1)

    requests_mock.get(service_connection.get_gdpr_url(), json={})

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 1
    # Data does not contain the empty response from service
    assert {} not in response_data


def test_when_service_does_not_have_gdpr_url_set_then_error_is_returned(
    user_gql_client, service_1
):
    service_1.gdpr_url = ""
    service_1.save()

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")


def test_when_service_does_not_have_gdpr_query_scope_set_then_error_is_returned(
    user_gql_client, service_1
):
    service_1.gdpr_query_scope = ""
    service_1.save()

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")


def test_api_tokens_missing(user_gql_client, service_1, mocker):
    """Missing API token for a service connection that has the query/delete scope set, should be an error."""
    mocker.patch.object(TunnistamoTokenExchange, "fetch_api_tokens", return_value={})
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, MISSING_GDPR_API_TOKEN_ERROR)


def test_when_service_fails_to_return_data_then_error_is_returned(
    user_gql_client, service_1, gdpr_api_tokens, mocker, requests_mock
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )

    profile = ProfileFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(profile=profile, service=service_1)

    requests_mock.get(service_connection.get_gdpr_url(), status_code=403)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")
