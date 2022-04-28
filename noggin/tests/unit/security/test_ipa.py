from unittest.mock import patch

import pytest
import requests
from cryptography.fernet import Fernet
from flask import current_app
from python_freeipa.exceptions import BadRequest, FreeIPAError

from noggin.app import ipa_admin
from noggin.security.ipa import (
    Client,
    maybe_ipa_login,
    maybe_ipa_session,
    untouched_ipa_client,
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
        assert sess.get('noggin_ipa_server_hostname') == "ipa.noggin.test"
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


def test_ipa_client_with_errors(ipa_call_error):
    with patch("noggin.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.unit.tests")
        result = client.group_add_member_manager(a_cn="dummy-group", o_user="dummy")
        assert result['failed'] == {
            'member': {'group': [], 'user': ['this is an error']}
        }


def test_ipa_client_skip_errors(ipa_call_error):
    with patch("noggin.security.ipa.Client._request") as request:
        request.return_value = ipa_call_error
        client = Client("ipa.unit.tests")
        result = client.group_add_member_manager(
            a_cn="dummy-group", o_user="dummy", skip_errors=True
        )
        assert result['result'] == "call-result"


@pytest.mark.vcr
def test_ipa_client_batch(client, logged_in_dummy_user, dummy_group):
    """Check the IPAClient batch method"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        result = ipa.batch(
            a_methods=[
                {"method": "user_find", "params": [["dummy"], {}]},
                {"method": "group_find", "params": [["dummy-group"], {}]},
            ]
        )
        assert result['count'] == 2
        assert result['results'][0]['result'][0]['uid'][0] == 'dummy'
        assert (
            result['results'][1]['result'][0]['description'][0]
            == 'The dummy-group group'
        )


@pytest.mark.vcr
def test_ipa_client_batch_no_raise_errors(client, logged_in_dummy_user, dummy_group):
    """Check the IPAClient batch method"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        result = ipa.batch(
            a_methods=[
                {"method": "user_find", "params": [["dummy"], {}]},
                {"method": "this_method_wont_work", "params": [["dummy-group"], {}]},
            ],
        )
        assert result['count'] == 2
        assert result['results'][0]['result'][0]['uid'][0] == 'dummy'
        assert result['results'][1]['error_name'] == 'CommandError'


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
    client = Client("ipa.unit.tests")
    with patch.object(client, "_session") as request:
        response = requests.Response()
        response.status_code = 400
        request.post.return_value = response
        with pytest.raises(FreeIPAError):
            client.change_password("dummy", "password", "password")


def test_ipa_client_change_password_empty_response():
    client = Client("ipa.unit.tests")
    with patch.object(client, "_session") as request:
        response = requests.Response()
        response.status_code = 200
        request.post.return_value = response
        with pytest.raises(FreeIPAError):
            client.change_password("dummy", "password", "password")


@pytest.mark.vcr
def test_ipa_client_fasagreement_find(client, logged_in_dummy_user, dummy_agreement):
    """Check the IPAClient fasagreement_find"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)

        result = ipa.fasagreement_find(all=True, cn="dummy agreement")

        assert len(result) == 1
        assert result[0]['cn'] == ['dummy agreement']


@pytest.mark.vcr
def test_ipa_client_fasagreement_add(client, logged_in_dummy_user, dummy_agreement):
    """Check the IPAClient fasagreement_add"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)

        # add a new agreement and check it is there
        ipa_admin.fasagreement_add("pants agreement")

        result = ipa.fasagreement_find(all=True, cn="pants agreement")
        assert len(result) == 1
        assert result[0]['cn'] == ['pants agreement']

        # cleanup
        ipa_admin.fasagreement_del("pants agreement")


@pytest.mark.vcr
def test_ipa_client_fasagreement_add_user(
    client, logged_in_dummy_user, dummy_agreement
):
    """Check the IPAClient fasagreement_add_user"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)

        # add a user to the agreement
        ipa.fasagreement_add_user("dummy agreement", user="dummy")

        # check it worked
        result = ipa.fasagreement_find(all=True, cn="dummy agreement")
        assert len(result) == 1
        assert result[0]["memberuser_user"] == ["dummy"]


@pytest.mark.vcr
def test_ipa_client_fasagreement_add_group(
    client, logged_in_dummy_user, dummy_group_with_agreement
):
    """Check the IPAClient fasagreement_add_group"""
    with client.session_transaction() as sess:
        ipa = maybe_ipa_session(current_app, sess)
        result = ipa.fasagreement_find(all=True, cn="dummy agreement")
        assert len(result) == 1
        assert result[0]["member_group"] == ["dummy-group"]
