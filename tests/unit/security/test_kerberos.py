from unittest import mock

import pytest

from noggin.security.kerberos import (
    KerberosAuthError,
    KerberosConfigError,
    ipa_login_with_kerberos,
    impersonate_user,
    load_service_credentials,
)


@pytest.fixture
def kerberos_config(client, mocker):
    """Patch app config with Kerberos keytab settings."""
    mocker.patch.dict(
        'flask.current_app.config',
        {
            'KERBEROS_KEYTAB': '/etc/noggin/noggin.keytab',
            'KERBEROS_SERVICE_PRINCIPAL': 'HTTP/noggin.example.com@EXAMPLE.COM',
            'FREEIPA_DOMAIN': 'example.com',
            'FREEIPA_CACERT': '/etc/ipa/ca.crt',
            'FERNET_SECRET': b'G8ObvrpEEwbjWUO9rU1qAkDQRafAFd39heVKYf6TZi8=',
        },
    )


class TestLoadServiceCredentials:

    def test_no_keytab_configured(self, client, mocker):
        mocker.patch.dict('flask.current_app.config', {'KERBEROS_KEYTAB': None})
        from flask import current_app

        with pytest.raises(KerberosConfigError, match="not configured"):
            load_service_credentials(current_app)

    def test_keytab_load_success(self, client, kerberos_config, mocker):
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mock_creds = mock.MagicMock()
        mock_gssapi.Credentials.return_value = mock_creds

        from flask import current_app

        result = load_service_credentials(current_app)
        assert result is mock_creds
        mock_gssapi.Credentials.assert_called_once()

    def test_keytab_load_gssapi_error(self, client, kerberos_config, mocker):
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mock_gssapi.exceptions.GSSError = type('GSSError', (Exception,), {})
        mock_gssapi.Credentials.side_effect = mock_gssapi.exceptions.GSSError(
            "keytab not found"
        )

        from flask import current_app

        with pytest.raises(KerberosConfigError, match="Cannot load"):
            load_service_credentials(current_app)

    def test_principal_derived_from_fqdn(self, client, mocker):
        mocker.patch.dict(
            'flask.current_app.config',
            {
                'KERBEROS_KEYTAB': '/etc/noggin/noggin.keytab',
                'KERBEROS_SERVICE_PRINCIPAL': None,
                'FREEIPA_DOMAIN': 'example.com',
            },
        )
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mocker.patch('noggin.security.kerberos.socket.getfqdn', return_value='noggin.example.com')
        mock_creds = mock.MagicMock()
        mock_gssapi.Credentials.return_value = mock_creds

        from flask import current_app

        load_service_credentials(current_app)

        call_args = mock_gssapi.Name.call_args
        assert call_args[0][0] == 'HTTP/noggin.example.com@EXAMPLE.COM'


class TestImpersonateUser:

    def test_success(self, mocker):
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mock_gssapi.exceptions.GSSError = type('GSSError', (Exception,), {})
        mock_service_creds = mock.MagicMock()
        mock_impersonated = mock.MagicMock()
        mock_service_creds.impersonate.return_value = mock_impersonated

        mock_ctx = mock.MagicMock()
        mock_ctx.step.return_value = b'\x60\x82token-bytes'
        mock_gssapi.SecurityContext.return_value = mock_ctx

        result = impersonate_user(
            mock_service_creds, 'testuser', 'HTTP/ipa.example.com@EXAMPLE.COM'
        )
        assert result == b'\x60\x82token-bytes'
        mock_service_creds.impersonate.assert_called_once()

    def test_gssapi_error(self, mocker):
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mock_gssapi.exceptions.GSSError = type('GSSError', (Exception,), {})
        mock_service_creds = mock.MagicMock()
        mock_service_creds.impersonate.side_effect = mock_gssapi.exceptions.GSSError(
            "permission denied"
        )

        with pytest.raises(KerberosAuthError, match="delegation failed"):
            impersonate_user(
                mock_service_creds, 'testuser', 'HTTP/ipa.example.com@EXAMPLE.COM'
            )

    def test_no_token_produced(self, mocker):
        mock_gssapi = mocker.patch('noggin.security.kerberos.gssapi')
        mock_gssapi.exceptions.GSSError = type('GSSError', (Exception,), {})
        mock_service_creds = mock.MagicMock()
        mock_impersonated = mock.MagicMock()
        mock_service_creds.impersonate.return_value = mock_impersonated

        mock_ctx = mock.MagicMock()
        mock_ctx.step.return_value = None
        mock_gssapi.SecurityContext.return_value = mock_ctx

        with pytest.raises(KerberosAuthError, match="no token"):
            impersonate_user(
                mock_service_creds, 'testuser', 'HTTP/ipa.example.com@EXAMPLE.COM'
            )


class TestIpaLoginWithKerberos:

    def _mock_common(self, mocker):
        """Set up common mocks for ipa_login_with_kerberos tests."""
        mocker.patch(
            'noggin.security.kerberos.load_service_credentials',
            return_value=mock.MagicMock(),
        )
        mocker.patch(
            'noggin.security.kerberos.choose_server',
            return_value='ipa.example.com',
        )
        mocker.patch(
            'noggin.security.kerberos.impersonate_user',
            return_value=b'spnego-token',
        )

    def test_successful_login(self, client, kerberos_config, mocker):
        self._mock_common(mocker)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.cookies.get.return_value = 'fake-ipa-session-cookie'
        mocker.patch(
            'noggin.security.kerberos.requests.post',
            return_value=mock_response,
        )

        from flask import current_app

        sess = {}
        result = ipa_login_with_kerberos(current_app, sess, 'testuser')
        assert result is not None
        assert sess['noggin_username'] == 'testuser'
        assert 'noggin_session' in sess

    def test_no_ipa_server(self, client, kerberos_config, mocker):
        mocker.patch(
            'noggin.security.kerberos.load_service_credentials',
            return_value=mock.MagicMock(),
        )
        mocker.patch(
            'noggin.security.kerberos.choose_server',
            side_effect=__import__(
                'noggin.security.ipa', fromlist=['NoIPAServer']
            ).NoIPAServer(),
        )

        from flask import current_app

        with pytest.raises(KerberosAuthError, match="No IPA server"):
            ipa_login_with_kerberos(current_app, {}, 'testuser')

    def test_http_error(self, client, kerberos_config, mocker):
        self._mock_common(mocker)

        mock_response = mock.MagicMock()
        mock_response.status_code = 401
        mocker.patch(
            'noggin.security.kerberos.requests.post',
            return_value=mock_response,
        )

        from flask import current_app

        with pytest.raises(KerberosAuthError, match="login failed"):
            ipa_login_with_kerberos(current_app, {}, 'testuser')

    def test_no_session_cookie(self, client, kerberos_config, mocker):
        self._mock_common(mocker)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.cookies.get.return_value = None
        mocker.patch(
            'noggin.security.kerberos.requests.post',
            return_value=mock_response,
        )

        from flask import current_app

        with pytest.raises(KerberosAuthError, match="did not return a session"):
            ipa_login_with_kerberos(current_app, {}, 'testuser')

    def test_request_exception(self, client, kerberos_config, mocker):
        self._mock_common(mocker)
        mocker.patch(
            'noggin.security.kerberos.requests.post',
            side_effect=__import__('requests').RequestException("timeout"),
        )

        from flask import current_app

        with pytest.raises(KerberosAuthError, match="Could not contact"):
            ipa_login_with_kerberos(current_app, {}, 'testuser')
