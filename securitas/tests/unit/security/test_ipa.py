from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from flask import current_app
from python_freeipa.exceptions import ValidationError

from securitas.security.ipa import (
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
        sess["securitas_session"] = "invalid"
        with pytest.raises(TypeError):
            maybe_ipa_session(current_app, sess)


@pytest.mark.vcr
def test_ipa_session_unauthorized(client, logged_in_dummy_user):
    """The user should be unauthorized when the session isn't valid for FreeIPA."""
    with client.session_transaction() as sess:
        sess["securitas_session"] = Fernet(current_app.config['FERNET_SECRET']).encrypt(
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
        assert sess.get('securitas_session')
        assert sess.get('securitas_ipa_server_hostname') == "ipa.example.com"
        assert sess.get('securitas_username') == "dummy"
        # Test that the session is valid Fernet
        ipa_session = Fernet(current_app.config['FERNET_SECRET']).decrypt(
            sess.get('securitas_session')
        )
        assert str(ipa_session, 'ascii').startswith("MagBearerToken=")


def test_ipa_untouched_client(client):
    with client.session_transaction() as sess:
        ipa = untouched_ipa_client(current_app)
        assert ipa is not None
        assert 'securitas_session' not in sess
        assert 'securitas_ipa_server_hostname' not in sess
        assert 'securitas_username' not in sess


def test_parse_group_management_error_member(ipa_call_error):
    with pytest.raises(ValidationError):
        parse_group_management_error(ipa_call_error)


def test_parse_group_management_error_membermanager(ipa_call_error):
    with pytest.raises(ValidationError):
        parse_group_management_error(ipa_call_error)


def test_ipa_client_with_errors(ipa_call_error):
    with patch("securitas.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.example.com")
        with pytest.raises(ValidationError):
            client.group_add_member_manager("dummy-group", users="dummy")


def test_ipa_client_skip_errors(ipa_call_error):
    with patch("securitas.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.example.com")
        result = client.group_add_member_manager(
            "dummy-group", users="dummy", skip_errors=True
        )
        assert result == "call-result"
