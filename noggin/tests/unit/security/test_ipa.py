from unittest.mock import patch

import pytest
import requests
from cryptography.fernet import Fernet
from flask import current_app
from python_freeipa.exceptions import ValidationError, BadRequest, FreeIPAError

from noggin.security.ipa import (
    maybe_ipa_session,
    maybe_ipa_login,
    untouched_ipa_client,
    parse_group_management_error,
    Client,
)


@pytest.fixture
def ipa_call_error():
    return {
        'result': 'call-result',
        'failed': {'member': {'user': ["this is an error"], 'group': []}},
    }


@pytest.mark.vcr
def test_ipa_session_authed(client, logged_in_dummy_user):
    """Check maybe_ipa_session() when a user is logged in"""
    with client.session_transaction() as sess:
        assert maybe_ipa_session(current_app, sess) is not None


def test_ipa_session_anonymous(client):
    """Check maybe_ipa_session() when no user is logged in"""
    with client.session_transaction() as sess:
        assert maybe_ipa_session(current_app, sess) is None


@pytest.mark.vcr
def test_ipa_session_invalid(client, logged_in_dummy_user):
    """We should raise an exception when the session can't be decrypted."""
    with client.session_transaction() as sess:
        sess["noggin_session"] = "invalid"
        with pytest.raises(TypeError):
            maybe_ipa_session(current_app, sess)


@pytest.mark.vcr
def test_ipa_session_unauthorized(client, logged_in_dummy_user):
    """The user should be unauthorized when the session isn't valid for FreeIPA."""
    with client.session_transaction() as sess:
        sess["noggin_session"] = Fernet(current_app.config['FERNET_SECRET']).encrypt(
            b'something-invalid'
        )
        ipa = maybe_ipa_session(current_app, sess)
    assert ipa is None


@pytest.mark.vcr
def test_ipa_login(client, dummy_user):
    with client.session_transaction() as sess:
        ipa = maybe_ipa_login(current_app, sess, "dummy", "dummy_password")
    assert ipa is not None
    with client.session_transaction() as sess:
        assert sess.get('noggin_session')
        assert sess.get('noggin_ipa_server_hostname') == "ipa.example.com"
        assert sess.get('noggin_username') == "dummy"
        # Test that the session is valid Fernet
        ipa_session = Fernet(current_app.config['FERNET_SECRET']).decrypt(
            sess.get('noggin_session')
        )
        assert str(ipa_session, 'ascii').startswith("MagBearerToken=")


def test_ipa_untouched_client(client):
    with client.session_transaction() as sess:
        ipa = untouched_ipa_client(current_app)
        assert ipa is not None
        assert 'noggin_session' not in sess
        assert 'noggin_ipa_server_hostname' not in sess
        assert 'noggin_username' not in sess


def test_parse_group_management_error_member(ipa_call_error):
    with pytest.raises(ValidationError):
        parse_group_management_error(ipa_call_error)


def test_parse_group_management_error_membermanager(ipa_call_error):
    with pytest.raises(ValidationError):
        parse_group_management_error(ipa_call_error)


def test_parse_group_management_error_keyerror(ipa_call_error):
    assert parse_group_management_error(ipa_call_error.pop('failed')) is None


def test_ipa_client_with_errors(ipa_call_error):
    with patch("noggin.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.example.com")
        with pytest.raises(ValidationError):
            client.group_add_member_manager("dummy-group", users="dummy")


def test_ipa_client_skip_errors(ipa_call_error):
    with patch("noggin.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.example.com")
        result = client.group_add_member_manager(
            "dummy-group", users="dummy", skip_errors=True
        )
        assert result == "call-result"


@pytest.mark.vcr
def test_ipa_client_batch(client, logged_in_dummy_user, dummy_group):
    """Check the IPAClient batch method"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        result = ipa.batch(
            methods=[
                {"method": "user_find", "params": [[], {"uid": "dummy", 'all': True}]},
                {"method": "group_find", "params": [["dummy-group"], {}]},
            ]
        )
        assert result['count'] == 2
        assert result['results'][0]['result'][0]['displayname'][0] == 'Dummy User'
        assert result['results'][1]['result'][0]['description'][0] == 'A dummy group'


@pytest.mark.vcr
def test_ipa_client_batch_no_raise_errors(client, logged_in_dummy_user, dummy_group):
    """Check the IPAClient batch method"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        result = ipa.batch(
            methods=[
                {"method": "user_find", "params": [[], {"uid": "dummy", 'all': True}]},
                {"method": "this_method_wont_work", "params": [["dummy-group"], {}]},
            ],
            raise_errors=False,
        )
        assert result['count'] == 2
        assert result['results'][0]['result'][0]['displayname'][0] == 'Dummy User'
        assert isinstance(result['results'][1], BadRequest)


@pytest.mark.vcr
def test_ipa_client_batch_unknown_method(client, logged_in_dummy_user):
    """Check the IPAClient batch method returns unknown command errors"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        with pytest.raises(BadRequest) as e:
            ipa.batch(methods=[{"method": "user_findy", "params": [[], {}]}])
            assert "unknown command 'user_findy'" in e


@pytest.mark.vcr
def test_ipa_client_batch_unknown_option(client, logged_in_dummy_user):
    """Check the IPAClient batch method returns invalid params errors"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        with pytest.raises(BadRequest) as e:
            ipa.batch(
                methods=[{"method": "user_find", "params": [[], {"pants": "pants"}]}]
            )
            assert "invalid 'params': Unknown option: pants" in e


def test_ipa_client_change_password_error():
    client = Client("ipa.example.com")
    with patch.object(client, "_session") as request:
        response = requests.Response()
        response.status_code = 400
        request.post.return_value = response
        with pytest.raises(FreeIPAError):
            client.change_password("dummy", "password", "password")


def test_ipa_client_change_password_empty_response():
    client = Client("ipa.example.com")
    with patch.object(client, "_session") as request:
        response = requests.Response()
        response.status_code = 200
        request.post.return_value = response
        with pytest.raises(FreeIPAError):
            client.change_password("dummy", "password", "password")
