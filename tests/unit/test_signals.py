from io import BytesIO

import pytest
import requests
from flask import current_app

from noggin.app import ipa_admin
from noggin.representation.user import User
from noggin.signals import request_basset_check
from noggin.utility.token import Audience, read_token


@pytest.mark.vcr()
def test_signal_basset(client, mocker, dummy_user):
    mocked_requests = mocker.patch("noggin.signals.requests")
    mocker.patch.dict(current_app.config, {"BASSET_URL": "http://basset.test"})
    user = User(ipa_admin.user_show("dummy")["result"])
    with current_app.test_request_context('/'):
        request_basset_check(user)
    call_args = mocked_requests.post.call_args_list[0]
    assert list(call_args[0]) == ["http://basset.test"]
    json_data = call_args[1]["json"]
    assert json_data["action"] == "fedora.noggin.registration"
    expected_dict = user.as_dict()
    expected_dict["human_name"] = user.commonname
    expected_dict["email"] = user.mail
    assert json_data["data"]["user"] == expected_dict
    assert json_data["data"]["request_headers"] == {"Host": "localhost"}
    assert json_data["data"]["callback"] == "http://localhost/register/spamcheck-hook"
    token = json_data["data"]["token"]
    token_data = read_token(token, audience=Audience.spam_check)
    assert token_data["sub"] == "dummy"


@pytest.mark.vcr()
def test_signal_basset_disabled(client, mocker, dummy_user):
    mocked_requests = mocker.patch("noggin.signals.requests")
    user = User(ipa_admin.user_show("dummy"))
    with current_app.test_request_context('/'):
        request_basset_check(user)
    mocked_requests.post.assert_not_called()


@pytest.mark.vcr()
def test_signal_basset_failed(client, mocker, dummy_user):
    mocked_requests = mocker.patch("noggin.signals.requests")
    failure = requests.Response()
    failure.status_code = 500
    failure.reason = "Server Error"
    failure.raw = BytesIO(b"nope.")
    mocked_requests.post.return_value = failure
    mocker.patch.dict(current_app.config, {"BASSET_URL": "http://basset.test"})
    logger = mocker.patch.object(current_app._get_current_object(), "logger")
    user = User(ipa_admin.user_show("dummy"))
    with current_app.test_request_context('/'):
        request_basset_check(user)
    mocked_requests.post.assert_called()
    logger.warning.assert_called_with(
        "Error requesting a Basset check: 500 Server Error: nope."
    )
