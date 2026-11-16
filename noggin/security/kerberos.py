import base64
import logging
import socket

import gssapi
import gssapi.raw
import requests
from cryptography.fernet import Fernet

from .ipa import Client, NoIPAServer, choose_server

logger = logging.getLogger(__name__)


class KerberosConfigError(Exception):
    """Kerberos is not configured or the keytab is unusable."""

    pass


class KerberosAuthError(Exception):
    """Kerberos authentication (S4U2Self/S4U2Proxy or SPNEGO) failed."""

    pass


def load_service_credentials(app):
    """Load GSSAPI credentials from the configured service keytab.

    Reads ``KERBEROS_KEYTAB`` and ``KERBEROS_SERVICE_PRINCIPAL`` from the app
    config.  If ``KERBEROS_SERVICE_PRINCIPAL`` is not set, it is derived from
    the machine FQDN and the FreeIPA domain.

    Returns a ``gssapi.Credentials`` object suitable for S4U2Self.

    Raises ``KerberosConfigError`` if the keytab is missing or unreadable.
    """
    keytab = app.config.get('KERBEROS_KEYTAB')
    if not keytab:
        raise KerberosConfigError("KERBEROS_KEYTAB is not configured")

    principal = app.config.get('KERBEROS_SERVICE_PRINCIPAL')
    if not principal:
        fqdn = socket.getfqdn()
        realm = app.config['FREEIPA_DOMAIN'].upper()
        principal = f"HTTP/{fqdn}@{realm}"

    try:
        name = gssapi.Name(principal, gssapi.NameType.kerberos_principal)
        creds = gssapi.Credentials(
            name=name,
            usage='both',
            store={'client_keytab': keytab, 'keytab': keytab},
        )
        return creds
    except gssapi.exceptions.GSSError as e:
        logger.error("Failed to load Kerberos credentials from %s: %s", keytab, e)
        raise KerberosConfigError(
            f"Cannot load Kerberos credentials: {e}"
        ) from e


def impersonate_user(service_creds, username, target_principal):
    """Perform S4U2Self + S4U2Proxy to obtain a SPNEGO token for the user.

    Uses the service credentials to impersonate ``username`` (S4U2Self / protocol
    transition), then initiates a security context to ``target_principal``
    (S4U2Proxy / constrained delegation).

    Returns the SPNEGO output token bytes.

    Raises ``KerberosAuthError`` on any GSSAPI failure.
    """
    try:
        user_name = gssapi.Name(username, gssapi.NameType.user)
        impersonated_creds = service_creds.impersonate(name=user_name)

        target_name = gssapi.Name(
            target_principal, gssapi.NameType.kerberos_principal
        )
        ctx = gssapi.SecurityContext(
            name=target_name,
            creds=impersonated_creds,
            usage='initiate',
        )
        token = ctx.step()
        if token is None:
            raise KerberosAuthError("GSSAPI security context produced no token")
        return bytes(token)
    except gssapi.exceptions.GSSError as e:
        logger.error(
            "S4U2Self/S4U2Proxy failed for user %s to %s: %s",
            username,
            target_principal,
            e,
        )
        raise KerberosAuthError(
            f"Kerberos delegation failed for user {username}"
        ) from e


def ipa_login_with_kerberos(app, session, username):
    """Establish an IPA session for ``username`` via Kerberos delegation.

    Performs the full S4U2Self + S4U2Proxy flow, then authenticates to the
    IPA server's ``/ipa/session/login_kerberos`` endpoint using SPNEGO.
    The resulting session cookie is encrypted and stored in the Flask session,
    exactly like ``maybe_ipa_login()`` does for password-based login.

    Returns a ``Client`` object with a valid IPA session, or raises
    ``KerberosConfigError`` / ``KerberosAuthError`` on failure.
    """
    service_creds = load_service_credentials(app)

    try:
        server = choose_server(app, session)
    except NoIPAServer:
        raise KerberosAuthError("No IPA server available")

    realm = app.config['FREEIPA_DOMAIN'].upper()
    target_principal = f"HTTP/{server}@{realm}"

    spnego_token = impersonate_user(service_creds, username, target_principal)

    url = f"https://{server}/ipa/session/login_kerberos"
    headers = {
        'Authorization': f'Negotiate {base64.b64encode(spnego_token).decode("ascii")}',
        'Referer': f'https://{server}/ipa',
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            verify=app.config['FREEIPA_CACERT'],
        )
    except requests.RequestException as e:
        logger.error("HTTP request to IPA login_kerberos failed: %s", e)
        raise KerberosAuthError("Could not contact the IPA server") from e

    if resp.status_code != 200:
        logger.error(
            "IPA login_kerberos returned %d for user %s",
            resp.status_code,
            username,
        )
        raise KerberosAuthError("IPA Kerberos login failed")

    ipa_session_cookie = resp.cookies.get('ipa_session')
    if not ipa_session_cookie:
        logger.error("IPA login_kerberos response has no ipa_session cookie")
        raise KerberosAuthError("IPA did not return a session")

    fernet = Fernet(app.config['FERNET_SECRET'])
    encrypted_session = fernet.encrypt(ipa_session_cookie.encode('utf-8'))
    session['noggin_session'] = encrypted_session
    session['noggin_username'] = username

    client = Client(server, verify_ssl=app.config['FREEIPA_CACERT'])
    client._current_host = server
    client._session.cookies['ipa_session'] = ipa_session_cookie

    return client
