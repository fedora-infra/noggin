import base64
import json
import time
from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup

from noggin.utility.passkey import (
    RegistrationResult,
    b64url_encode,
    format_passkey_attr,
    parse_passkey_attr,
)

from ..utilities import assert_redirects_with_flash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_show_result(username="dummy", passkeys=None, locked=False):
    """Build a minimal user_show result dict suitable for the controller."""
    result = {
        'uid': [username],
        'cn': [f'{username.title()} User'],
        'givenname': [username.title()],
        'sn': ['User'],
        'mail': [f'{username}@unit.tests'],
        'nsaccountlock': locked,
    }
    if passkeys is not None:
        result['ipapasskey'] = passkeys
    return result


def _make_whoami_result(username="dummy"):
    """Build a minimal user_find(whoami=True) result list."""
    return [_make_user_show_result(username)]


def _make_passkey_value(cred_id=b'\x01\x02\x03\x04', spki_der=b'\x30\x59' + b'\x00' * 89):
    """Build a passkey attribute value string for testing.

    Uses raw base64 encoding of credential ID and SPKI DER bytes.
    """
    cred_b64 = base64.b64encode(cred_id).decode('ascii')
    key_b64 = base64.b64encode(spki_der).decode('ascii')
    return f"passkey:{cred_b64},{key_b64}"


SAMPLE_CRED_ID = b'\xaa\xbb\xcc\xdd' * 4
SAMPLE_SPKI_DER = b'\x30\x59' + b'\x00' * 89
SAMPLE_PASSKEY = _make_passkey_value(SAMPLE_CRED_ID, SAMPLE_SPKI_DER)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ipa(client, mocker):
    """Provide a mock IPA client and set up the session as if the user is logged in.

    Patches ``maybe_ipa_session`` so the ``@with_ipa()`` decorator receives our
    mock instead of trying to contact a real FreeIPA server.
    """
    mock_client = mock.MagicMock()

    # Default behaviour: user_find(whoami=True) returns dummy user
    mock_client.user_find.return_value = {'result': _make_whoami_result()}

    # Default: user_show returns dummy user with no passkeys
    mock_client.user_show.return_value = {'result': _make_user_show_result()}

    # Patch maybe_ipa_session to return our mock
    mocker.patch(
        'noggin.utility.controllers.maybe_ipa_session', return_value=mock_client
    )

    # Set session variables that with_ipa and require_self need
    with client.session_transaction() as sess:
        sess['noggin_session'] = b'fake-encrypted-session'
        sess['noggin_username'] = 'dummy'
        sess['noggin_ipa_server_hostname'] = 'ipa.tinystage.test'

    yield mock_client


# ---------------------------------------------------------------------------
# GET /user/<username>/settings/passkeys/
# ---------------------------------------------------------------------------

class TestPasskeysPage:

    def test_empty_passkey_list(self, client, mock_ipa):
        """Logged-in user sees the page with an empty passkey list."""
        result = client.get('/user/dummy/settings/passkeys/')
        assert result.status_code == 200

        page = BeautifulSoup(result.data, 'html.parser')
        assert page.title
        assert 'dummy' in page.title.string

        pageheading = page.select_one('#pageheading')
        assert pageheading is not None
        assert pageheading.get_text(strip=True) == 'Passkeys'

        # Should show the "no passkeys" message
        list_items = page.select('div.list-group .list-group-item')
        assert len(list_items) == 1
        text = list_items[0].get_text(strip=True)
        assert 'You have no passkeys' in text

    def test_passkeys_displayed(self, client, mock_ipa):
        """Logged-in user sees passkeys when they exist."""
        mock_ipa.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        result = client.get('/user/dummy/settings/passkeys/')
        assert result.status_code == 200

        page = BeautifulSoup(result.data, 'html.parser')
        list_items = page.select('div.list-group .list-group-item')
        # Should have one real passkey item, not the "no passkeys" message
        assert len(list_items) >= 1
        full_text = ' '.join(item.get_text(strip=True) for item in list_items)
        assert 'You have no passkeys' not in full_text

        # The display_id should appear on the page (hex prefix of credential_id)
        display_id = SAMPLE_CRED_ID.hex()[:16]
        assert display_id in page.get_text()

    def test_cannot_view_other_user(self, client, mock_ipa):
        """Cannot view another user's passkeys; redirects with flash."""
        result = client.get('/user/otheruser/settings/passkeys/')
        assert_redirects_with_flash(
            result,
            expected_url='/user/otheruser/',
            expected_message='You do not have permission to edit this account.',
            expected_category='danger',
        )


# ---------------------------------------------------------------------------
# POST /user/<username>/settings/passkeys/register-begin
# ---------------------------------------------------------------------------

class TestRegisterBegin:

    def test_returns_valid_json(self, client, mock_ipa):
        """POST register-begin returns valid JSON with challenge, rp, user info."""
        result = client.post('/user/dummy/settings/passkeys/register-begin')
        assert result.status_code == 200

        data = result.get_json()
        assert data is not None

        # Check required fields
        assert 'challenge' in data
        assert isinstance(data['challenge'], str)
        assert len(data['challenge']) > 0

        assert 'rp' in data
        assert data['rp']['id'] == 'tinystage.test'
        assert data['rp']['name'] == 'Noggin'

        assert 'user' in data
        assert data['user']['name'] == 'dummy'
        assert 'id' in data['user']
        assert 'displayName' in data['user']

        assert 'pubKeyCredParams' in data
        assert 'authenticatorSelection' in data
        assert 'timeout' in data
        assert 'attestation' in data

    def test_stores_challenge_in_session(self, client, mock_ipa):
        """POST register-begin stores challenge data in the session."""
        result = client.post('/user/dummy/settings/passkeys/register-begin')
        assert result.status_code == 200

        data = result.get_json()

        with client.session_transaction() as sess:
            assert 'noggin_passkey_challenge' in sess
            assert sess['noggin_passkey_challenge'] == data['challenge']
            assert sess['noggin_passkey_challenge_username'] == 'dummy'
            assert 'noggin_passkey_challenge_time' in sess

    def test_exclude_credentials_with_existing_passkeys(self, client, mock_ipa):
        """register-begin includes excludeCredentials when user has passkeys."""
        mock_ipa.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[SAMPLE_PASSKEY])
        }

        result = client.post('/user/dummy/settings/passkeys/register-begin')
        assert result.status_code == 200

        data = result.get_json()
        assert 'excludeCredentials' in data
        assert len(data['excludeCredentials']) == 1
        assert data['excludeCredentials'][0]['type'] == 'public-key'


# ---------------------------------------------------------------------------
# POST /user/<username>/settings/passkeys/register-complete
# ---------------------------------------------------------------------------

class TestRegisterComplete:

    def test_missing_challenge_returns_400(self, client, mock_ipa):
        """register-complete returns 400 when no challenge is in the session."""
        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({'response': {'clientDataJSON': 'x', 'attestationObject': 'y'}}),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'error' in data

    def test_username_mismatch_returns_400(self, client, mock_ipa):
        """register-complete returns 400 when the stored username doesn't match."""
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'otheruser'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({'response': {'clientDataJSON': 'x', 'attestationObject': 'y'}}),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'error' in data

    def test_expired_challenge_returns_400(self, client, mock_ipa):
        """register-complete returns 400 when the challenge has expired (>300s)."""
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            # Set the time to 301 seconds ago
            sess['noggin_passkey_challenge_time'] = time.time() - 301

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({'response': {'clientDataJSON': 'x', 'attestationObject': 'y'}}),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'expired' in data['error'].lower()

    def test_missing_request_body_returns_400(self, client, mock_ipa):
        """register-complete returns 400 when the request body is null/empty."""
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        # JSON null yields get_json() == None in the handler
        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps(None),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert data is not None
        assert 'error' in data

    def test_missing_attestation_data_returns_400(self, client, mock_ipa):
        """register-complete returns 400 when attestation fields are missing."""
        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({'response': {}}),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'error' in data

    def test_successful_registration(self, client, mock_ipa, mocker):
        """register-complete succeeds when verify_registration passes."""
        fake_cred_id = b'\x11\x22\x33\x44' * 4
        fake_cose_key = b'\xaa\xbb\xcc\xdd' * 8

        # Mock verify_registration to return a successful result
        mock_verify = mocker.patch(
            'noggin.controller.user.verify_registration',
            return_value=RegistrationResult(
                credential_id=fake_cred_id,
                public_key_cose=fake_cose_key,
            ),
        )

        # Mock format_passkey_attr to return a predictable value
        mocker.patch(
            'noggin.controller.user.format_passkey_attr',
            return_value='passkey:fakedata',
        )

        # user_show for duplicate check returns no existing passkeys
        mock_ipa.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[])
        }

        # passkey_add succeeds
        mock_ipa.passkey_add.return_value = {'result': {}}

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'attestationObject': 'fake-att',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 200
        data = result.get_json()
        assert data['ok'] is True

        # Verify that passkey_add was called
        mock_ipa.passkey_add.assert_called_once_with('dummy', 'passkey:fakedata')

        # Verify that verify_registration was called with the right params
        mock_verify.assert_called_once()

    def test_ipa_error_returns_500(self, client, mock_ipa, mocker):
        """register-complete returns 500 with a generic message on IPA error."""
        fake_cred_id = b'\x11\x22\x33\x44' * 4
        fake_cose_key = b'\xaa\xbb\xcc\xdd' * 8

        mocker.patch(
            'noggin.controller.user.verify_registration',
            return_value=RegistrationResult(
                credential_id=fake_cred_id,
                public_key_cose=fake_cose_key,
            ),
        )
        mocker.patch(
            'noggin.controller.user.format_passkey_attr',
            return_value='passkey:fakedata',
        )

        mock_ipa.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[])
        }
        mock_ipa.passkey_add.side_effect = python_freeipa.exceptions.FreeIPAError(
            message='Internal server details that should not be leaked',
            code='4242',
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'attestationObject': 'fake-att',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 500
        data = result.get_json()
        assert 'error' in data
        # The response should NOT leak internal IPA error details
        assert 'Internal server details' not in data['error']
        assert 'try again' in data['error'].lower()

    def test_duplicate_credential_returns_409(self, client, mock_ipa, mocker):
        """register-complete returns 409 when the credential is already registered."""
        # Use the same credential ID as what's already stored
        existing_cred_id = b'\x11\x22\x33\x44' * 4
        existing_passkey = _make_passkey_value(existing_cred_id)

        mocker.patch(
            'noggin.controller.user.verify_registration',
            return_value=RegistrationResult(
                credential_id=existing_cred_id,
                public_key_cose=b'\xaa' * 32,
            ),
        )

        # user_show returns user with an existing passkey whose credential_id matches
        mock_ipa.user_show.return_value = {
            'result': _make_user_show_result(passkeys=[existing_passkey])
        }

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'attestationObject': 'fake-att',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 409
        data = result.get_json()
        assert 'already registered' in data['error'].lower()

    def test_verification_failure_returns_400(self, client, mock_ipa, mocker):
        """register-complete returns 400 when verify_registration raises ValueError."""
        mocker.patch(
            'noggin.controller.user.verify_registration',
            side_effect=ValueError('Challenge mismatch'),
        )

        challenge_b64 = b64url_encode(b'\x00' * 32)
        with client.session_transaction() as sess:
            sess['noggin_passkey_challenge'] = challenge_b64
            sess['noggin_passkey_challenge_username'] = 'dummy'
            sess['noggin_passkey_challenge_time'] = time.time()

        result = client.post(
            '/user/dummy/settings/passkeys/register-complete',
            data=json.dumps({
                'response': {
                    'clientDataJSON': 'fake-cdj',
                    'attestationObject': 'fake-att',
                },
            }),
            content_type='application/json',
        )
        assert result.status_code == 400
        data = result.get_json()
        assert 'error' in data


# ---------------------------------------------------------------------------
# POST /user/<username>/settings/passkeys/delete/
# ---------------------------------------------------------------------------

class TestPasskeyDelete:

    def test_successful_deletion(self, client, mock_ipa):
        """POST delete with a valid passkey value flashes success and redirects."""
        mock_ipa.passkey_del.return_value = {'result': {}}

        result = client.post(
            '/user/dummy/settings/passkeys/delete/',
            data={'passkey': SAMPLE_PASSKEY},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/dummy/settings/passkeys/',
            expected_message='The passkey has been removed.',
            expected_category='success',
        )
        mock_ipa.passkey_del.assert_called_once_with('dummy', SAMPLE_PASSKEY)

    def test_empty_passkey_flashes_danger(self, client, mock_ipa):
        """POST delete with an empty passkey field flashes a validation error."""
        result = client.post(
            '/user/dummy/settings/passkeys/delete/',
            data={'passkey': ''},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/dummy/settings/passkeys/',
            expected_message='Passkey must not be empty',
            expected_category='danger',
        )

    def test_missing_passkey_field_flashes_danger(self, client, mock_ipa):
        """POST delete with no passkey field flashes a validation error."""
        result = client.post(
            '/user/dummy/settings/passkeys/delete/',
            data={},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/dummy/settings/passkeys/',
            expected_message='Passkey must not be empty',
            expected_category='danger',
        )

    def test_ipa_error_flashes_danger(self, client, mock_ipa):
        """POST delete flashes danger when IPA raises FreeIPAError."""
        mock_ipa.passkey_del.side_effect = python_freeipa.exceptions.FreeIPAError(
            message='Something went wrong', code='4242'
        )

        result = client.post(
            '/user/dummy/settings/passkeys/delete/',
            data={'passkey': SAMPLE_PASSKEY},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/dummy/settings/passkeys/',
            expected_message='Cannot delete the passkey.',
            expected_category='danger',
        )

    def test_ipa_bad_request_flashes_danger(self, client, mock_ipa):
        """POST delete flashes danger when IPA raises BadRequest."""
        mock_ipa.passkey_del.side_effect = python_freeipa.exceptions.BadRequest(
            message='Bad request', code='4242'
        )

        result = client.post(
            '/user/dummy/settings/passkeys/delete/',
            data={'passkey': SAMPLE_PASSKEY},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/dummy/settings/passkeys/',
            expected_message='Cannot delete the passkey.',
            expected_category='danger',
        )

    def test_no_permission_for_other_user(self, client, mock_ipa):
        """Cannot delete another user's passkey; redirects with flash."""
        result = client.post(
            '/user/otheruser/settings/passkeys/delete/',
            data={'passkey': SAMPLE_PASSKEY},
        )
        assert_redirects_with_flash(
            result,
            expected_url='/user/otheruser/',
            expected_message='You do not have permission to edit this account.',
            expected_category='danger',
        )
