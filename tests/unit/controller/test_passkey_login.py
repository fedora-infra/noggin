import base64
import json
import time
from unittest import mock

import pytest
import python_freeipa

from noggin.utility.passkey import AssertionResult, b64url_encode

from ..utilities import make_srv


def _make_user_show_result(username="dummy", passkeys=None):
    result = {
        'uid': [username],
        'cn': [f'{username.title()} User'],
        'givenname': [username.title()],
        'sn': ['User'],
        'mail': [f'{username}@unit.tests'],
        'nsaccountlock': False,
    }
    if passkeys is not None:
        result['ipapasskey'] = passkeys
    return result


def _make_passkey_value(cred_id=b'\x01\x02\x03\x04', spki_der=b'\x30\x59' + b'\x00' * 89):
    cred_b64 = base64.b64encode(cred_id).decode('ascii')
    key_b64 = base64.b64encode(spki_der).decode('ascii')
    return f"passkey:{cred_b64},{key_b64}"


SAMPLE_CRED_ID = b'\xaa\xbb\xcc\xdd' * 4
SAMPLE_SPKI_DER = b'\x30\x59' + b'\x00' * 89
SAMPLE_PASSKEY = _make_passkey_value(SAMPLE_CRED_ID, SAMPLE_SPKI_DER)


@pytest.fixture
def passkey_client(app, ipa_cert, srvlookup_mock, mocker):
    """Test client with KERBEROS_KEYTAB enabled."""
    mocker.patch.dict(app.config, {'KERBEROS_KEYTAB': '/etc/noggin/test.keytab'})
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def mock_ipa_admin(passkey_client, mocker):
    """Mock ipa_admin for user lookups."""
    mock_admin = mock.MagicMock()
    mocker.patch('noggin.controller.authentication.ipa_admin', mock_admin)
    return mock_admin


# ---------------------------------------------------------------------------
# POST /passkey/login-begin
# ---------------------------------------------------------------------------


class TestPasskeyLoginBegin:

    def test_returns_valid_json(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'dummy'}),
            content_type='application/json',
        )
        assert result.status_code == 200

        data = result.get_json()
        assert 'challenge' in data
        assert 'rpId' in data
        assert 'allowCredentials' in data
        assert len(data['allowCredentials']) == 1
        assert data['allowCredentials'][0]['type'] == 'public-key'
        assert 'timeout' in data

    def test_stores_challenge_in_session(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'dummy'}),
            content_type='application/json',
        )
        assert result.status_code == 200

        with passkey_client.session_transaction() as sess:
            assert 'noggin_passkey_auth_challenge' in sess
            assert sess['noggin_passkey_auth_username'] == 'dummy'
            assert 'noggin_passkey_auth_time' in sess

    def test_missing_username(self, passkey_client, mock_ipa_admin):
        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': ''}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'error' in result.get_json()

    def test_missing_body(self, passkey_client, mock_ipa_admin):
        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps(None),
            content_type='application/json',
        )
        assert result.status_code == 400

    def test_user_not_found(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.side_effect = python_freeipa.exceptions.NotFound(
            message='User not found', code='4001'
        )

        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'nonexistent'}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'not found' in result.get_json()['error'].lower()

    def test_user_no_passkeys(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[])
        }

        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'dummy'}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'no passkeys' in result.get_json()['error'].lower()

    def test_ipa_error(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.side_effect = python_freeipa.exceptions.FreeIPAError(
            message='Server error', code='5000'
        )

        result = passkey_client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'dummy'}),
            content_type='application/json',
        )
        assert result.status_code == 500

    def test_disabled_when_no_keytab(self, client):
        """Passkey login returns 400 when KERBEROS_KEYTAB is not set."""
        result = client.post(
            '/passkey/login-begin',
            data=json.dumps({'username': 'dummy'}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'not available' in result.get_json()['error'].lower()


# ---------------------------------------------------------------------------
# POST /passkey/login-complete
# ---------------------------------------------------------------------------


class TestPasskeyLoginComplete:

    def test_missing_challenge(self, passkey_client, mock_ipa_admin):
        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'x',
                    'authenticatorData': 'y',
                    'signature': 'z',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'error' in data

    def test_expired_challenge(self, passkey_client, mock_ipa_admin):
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time() - 301

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'x',
                    'authenticatorData': 'y',
                    'signature': 'z',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'expired' in result.get_json()['error'].lower()

    def test_missing_request_body(self, passkey_client, mock_ipa_admin):
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps(None),
            content_type='application/json',
        )
        assert result.status_code == 400

    def test_missing_assertion_data(self, passkey_client, mock_ipa_admin):
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({'id': 'abc', 'response': {}}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'missing' in result.get_json()['error'].lower()

    def test_unknown_credential(self, passkey_client, mock_ipa_admin):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        unknown_cred = b'\xff' * 16
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(unknown_cred),
                'response': {
                    'clientDataJSON': 'x',
                    'authenticatorData': 'y',
                    'signature': 'z',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'unknown' in result.get_json()['error'].lower()

    def test_verification_failure(self, passkey_client, mock_ipa_admin, mocker):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        mocker.patch(
            'noggin.controller.authentication.verify_assertion',
            side_effect=ValueError('Challenge mismatch'),
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'authenticatorData': 'fake-ad',
                    'signature': 'fake-sig',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'verification failed' in result.get_json()['error'].lower()

    def test_successful_login(self, passkey_client, mock_ipa_admin, mocker):
        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        mocker.patch(
            'noggin.controller.authentication.verify_assertion',
            return_value=AssertionResult(credential_id=SAMPLE_CRED_ID),
        )

        mock_krb_login = mocker.patch(
            'noggin.controller.authentication.ipa_login_with_kerberos',
            return_value=mock.MagicMock(),
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'authenticatorData': 'fake-ad',
                    'signature': 'fake-sig',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 200
        data = result.get_json()
        assert data['ok'] is True
        assert 'redirect' in data
        mock_krb_login.assert_called_once()

    def test_kerberos_auth_failure(self, passkey_client, mock_ipa_admin, mocker):
        from noggin.security.kerberos import KerberosAuthError

        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        mocker.patch(
            'noggin.controller.authentication.verify_assertion',
            return_value=AssertionResult(credential_id=SAMPLE_CRED_ID),
        )

        mocker.patch(
            'noggin.controller.authentication.ipa_login_with_kerberos',
            side_effect=KerberosAuthError("delegation failed"),
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'authenticatorData': 'fake-ad',
                    'signature': 'fake-sig',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 500
        assert 'session' in result.get_json()['error'].lower()

    def test_kerberos_config_error(self, passkey_client, mock_ipa_admin, mocker):
        from noggin.security.kerberos import KerberosConfigError

        mock_ipa_admin.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        mocker.patch(
            'noggin.controller.authentication.verify_assertion',
            return_value=AssertionResult(credential_id=SAMPLE_CRED_ID),
        )

        mocker.patch(
            'noggin.controller.authentication.ipa_login_with_kerberos',
            side_effect=KerberosConfigError("keytab missing"),
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with passkey_client.session_transaction() as sess:
            sess['noggin_passkey_auth_challenge'] = challenge_b64
            sess['noggin_passkey_auth_username'] = 'dummy'
            sess['noggin_passkey_auth_time'] = time.time()

        result = passkey_client.post(
            '/passkey/login-complete',
            data=json.dumps({
                'id': b64url_encode(SAMPLE_CRED_ID),
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'authenticatorData': 'fake-ad',
                    'signature': 'fake-sig',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 500
        assert 'not available' in result.get_json()['error'].lower()

    def test_disabled_when_no_keytab(self, client):
        result = client.post(
            '/passkey/login-complete',
            data=json.dumps({}),
            content_type='application/json',
        )
        assert result.status_code == 400
        assert 'not available' in result.get_json()['error'].lower()
