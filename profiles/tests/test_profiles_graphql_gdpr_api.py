import json

import pytest
import requests

from open_city_profile.consts import (
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    MISSING_GDPR_API_TOKEN_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory
from users.models import User

from ..models import Profile
from .factories import ProfileFactory, ProfileWithPrimaryEmailFactory

AUTHORIZATION_CODE = "code123"
DOWNLOAD_MY_PROFILE_MUTATION = """
    {
        downloadMyProfile(authorizationCode: "code123")
    }
"""
DELETE_MY_PROFILE_MUTATION = """
    mutation {
        deleteMyProfile(input: {authorizationCode: "code123"}) {
            clientMutationId
        }
    }
"""
SCOPE_1 = "https://api.hel.fi/auth/api-1"
SCOPE_2 = "https://api.hel.fi/auth/api-2"
API_TOKEN_1 = "api_token_1"
API_TOKEN_2 = "api_token_2"
GDPR_API_TOKENS = {
    SCOPE_1: API_TOKEN_1,
    SCOPE_2: API_TOKEN_2,
}


@pytest.fixture
def berth_service(service_factory):
    return service_factory(
        name="service-1",
        gdpr_url="https://example-1.com/",
        gdpr_query_scope=f"{SCOPE_1}.gdprquery",
        gdpr_delete_scope=f"{SCOPE_1}.gdprdelete",
    )


@pytest.fixture
def youth_service(service_factory):
    return service_factory(
        name="service-2",
        gdpr_url="https://example-2.com/",
        gdpr_query_scope=f"{SCOPE_2}.gdprquery",
        gdpr_delete_scope=f"{SCOPE_2}.gdprdelete",
    )


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_user_can_download_profile(
    user_gql_client, service, mocker, with_serviceconnection
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    service_connection_created_at = None
    if with_serviceconnection:
        mocker.patch.object(
            TunnistamoTokenExchange, "fetch_api_tokens", return_value=None
        )
        service_connection = ServiceConnectionFactory(profile=profile, service=service)
        service_connection_created_at = service_connection.created_at.date().isoformat()

    primary_email = profile.emails.first()

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION, service=service)

    if with_serviceconnection:
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
                                            {
                                                "key": "EMAIL",
                                                "value": primary_email.email,
                                            },
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
                                            {"key": "SERVICE", "value": service.name},
                                            {
                                                "key": "CREATED_AT",
                                                "value": service_connection_created_at,
                                            },
                                        ],
                                    },
                                ],
                            },
                            {"key": "SUBSCRIPTIONS", "children": []},
                        ],
                    }
                ],
            }
        )
        assert executed["data"]["downloadMyProfile"] == expected_json, executed
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["downloadMyProfile"] is None


def test_downloading_non_existent_profile_doesnt_return_errors(user_gql_client):
    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert "errors" not in executed


def test_user_can_download_profile_with_connected_services(
    user_gql_client, youth_service, berth_service, mocker
):
    expected = {"key": "BERTH", "children": [{"key": "CUSTOMERID", "value": "123"}]}

    def mock_download_gdpr_data(self, api_token: str):
        if self.service.name == berth_service.name:
            return expected
        else:
            return {}

    mocker.patch.object(
        ServiceConnection,
        "download_gdpr_data",
        autospec=True,
        side_effect=mock_download_gdpr_data,
    )
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=berth_service)
    ServiceConnectionFactory(profile=profile, service=youth_service)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 2
    assert expected in response_data

    # Data does not contain the empty response from youth membership
    assert {} not in response_data


def test_user_can_download_profile_using_correct_api_tokens(
    user_gql_client, youth_service, berth_service, mocker
):
    def mock_download_gdpr_data(self, api_token: str):
        if (self.service.name == berth_service.name and api_token == API_TOKEN_1) or (
            self.service.name == youth_service.name and api_token == API_TOKEN_2
        ):
            return {}

        raise Exception("Wrong token used!")

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=berth_service)
    ServiceConnectionFactory(profile=profile, service=youth_service)
    mocked_gdpr_download = mocker.patch.object(
        ServiceConnection,
        "download_gdpr_data",
        autospec=True,
        side_effect=mock_download_gdpr_data,
    )
    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    mocked_token_exchange.assert_called_once()
    assert mocked_token_exchange.call_args == ((AUTHORIZATION_CODE,),)
    assert mocked_gdpr_download.call_count == 2
    assert executed["data"]["downloadMyProfile"]


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_user_can_delete_his_profile(
    user_gql_client, youth_service, requests_mock, mocker, with_serviceconnection
):
    """Deletion is allowed when GDPR URL is set, and service returns a successful status."""
    profile = ProfileFactory(user=user_gql_client.user)
    requests_mock.delete(
        f"{youth_service.gdpr_url}{profile.pk}", json={}, status_code=204
    )

    if with_serviceconnection:
        ServiceConnectionFactory(profile=profile, service=youth_service)
        mocker.patch.object(
            TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
        )

    executed = user_gql_client.execute(
        DELETE_MY_PROFILE_MUTATION, service=youth_service
    )

    expected_data = {"deleteMyProfile": {"clientMutationId": None}}

    if with_serviceconnection:
        assert executed["data"] == expected_data

        with pytest.raises(Profile.DoesNotExist):
            profile.refresh_from_db()
        with pytest.raises(User.DoesNotExist):
            user_gql_client.user.refresh_from_db()
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["deleteMyProfile"] is None
        assert Profile.objects.filter(pk=profile.pk).exists()


def test_user_tries_deleting_his_profile_but_it_fails_partially(
    user_gql_client, youth_service, berth_service, mocker
):
    """Test an edge case where dry runs passes for all connected services, but the
    proper service connection delete fails for a single connected service. All other
    connected services should still get deleted.
    """

    def mock_delete_gdpr_data(self, api_token, dry_run=False):
        if self.service.name == berth_service.name and not dry_run:
            raise requests.HTTPError("Such big fail! :(")

    mocker.patch.object(
        ServiceConnection,
        "delete_gdpr_data",
        autospec=True,
        side_effect=mock_delete_gdpr_data,
    )
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=youth_service)
    ServiceConnectionFactory(profile=profile, service=berth_service)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}

    assert ServiceConnection.objects.count() == 1
    assert ServiceConnection.objects.first().service == berth_service
    assert dict(executed["data"]) == expected_data
    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_FAILED_ERROR)


@pytest.mark.parametrize(
    "gdpr_url, response_status",
    [("", 204), ("", 405), ("https://gdpr-url.example/", 405)],
)
def test_user_cannot_delete_his_profile_if_service_doesnt_allow_it(
    user_gql_client, youth_service, requests_mock, gdpr_url, response_status, mocker
):
    """Profile cannot be deleted if connected service doesn't have GDPR URL configured or if the service
    returns a failed status for the dry_run call.
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileFactory(user=user_gql_client.user)
    requests_mock.delete(
        f"{gdpr_url}{profile.pk}", json={}, status_code=response_status
    )
    youth_service.gdpr_url = gdpr_url
    youth_service.save()
    ServiceConnectionFactory(profile=profile, service=youth_service)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}
    assert dict(executed["data"]) == expected_data
    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)


def test_user_gets_error_when_deleting_non_existent_profile(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    profile.delete()

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}
    assert dict(executed["data"]) == expected_data
    assert_match_error_code(executed, PROFILE_DOES_NOT_EXIST_ERROR)


def test_user_can_delete_his_profile_using_correct_api_tokens(
    user_gql_client, youth_service, berth_service, mocker
):
    def mock_delete_gdpr_data(self, api_token, dry_run=False):
        if (self.service.name == berth_service.name and api_token == API_TOKEN_1) or (
            self.service.name == youth_service.name and api_token == API_TOKEN_2
        ):
            return True

        raise Exception("Wrong token used!")

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=berth_service)
    ServiceConnectionFactory(profile=profile, service=youth_service)
    mocked_gdpr_delete = mocker.patch.object(
        ServiceConnection,
        "delete_gdpr_data",
        autospec=True,
        side_effect=mock_delete_gdpr_data,
    )
    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    mocked_token_exchange.assert_called_once()
    assert mocked_token_exchange.call_args == ((AUTHORIZATION_CODE,),)
    assert mocked_gdpr_delete.call_count == 4

    expected_data = {"deleteMyProfile": {"clientMutationId": None}}
    assert dict(executed["data"]) == expected_data
    with pytest.raises(Profile.DoesNotExist):
        profile.refresh_from_db()
    with pytest.raises(User.DoesNotExist):
        user_gql_client.user.refresh_from_db()


def test_service_doesnt_have_gdpr_query_scope_set(
    user_gql_client, berth_service, mocker
):
    """Missing query scope should make the query skip the service for a given connected profile."""
    berth_service.gdpr_query_scope = ""
    berth_service.save()
    berth_response = {
        "key": "BERTH",
        "children": [{"key": "CUSTOMERID", "value": "123"}],
    }
    mocker.patch.object(
        ServiceConnection, "download_gdpr_data", return_value=berth_response
    )
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=berth_service)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 1
    assert berth_response not in response_data


def test_service_doesnt_have_gdpr_delete_scope_set(
    user_gql_client, berth_service, mocker
):
    """Missing delete scope shouldn't allow deleting a connected profile."""
    berth_service.gdpr_delete_scope = ""
    berth_service.save()
    berth_response = {
        "key": "BERTH",
        "children": [{"key": "CUSTOMERID", "value": "123"}],
    }
    mocker.patch.object(
        ServiceConnection, "download_gdpr_data", return_value=berth_response
    )
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=berth_service)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)


@pytest.mark.parametrize("query_or_delete", ["query", "delete"])
def test_api_tokens_missing(user_gql_client, youth_service, query_or_delete, mocker):
    """Missing API token for a service connection that has the query/delete scope set, should be an error."""
    mocker.patch.object(TunnistamoTokenExchange, "fetch_api_tokens", return_value={})
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=youth_service)

    if query_or_delete == "query":
        executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)
    else:
        executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, MISSING_GDPR_API_TOKEN_ERROR)
