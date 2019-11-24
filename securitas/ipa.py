from cryptography.fernet import Fernet
import python_freeipa
from python_freeipa import Client
from flask import flash, session

# Attempt to obtain an IPA session from a cookie.
#
# If we are given a token as a cookie in the request, decrypt it and see if we
# are left with a valid IPA session.
#
# NOTE: You *MUST* check the result of this function every time you call it.
# It will be None if no session was provided or was provided but invalid.
def maybe_ipa_session(app):
    encrypted_session = session.get('securitas_session', None)
    if encrypted_session:
        fernet = Fernet(app.config['FERNET_SECRET'])
        ipa_session = fernet.decrypt(encrypted_session)
        client = Client(
            app.config['FREEIPA_SERVER'],
            verify_ssl=app.config['FREEIPA_CACERT'])
        client._session.cookies['ipa_session'] = str(ipa_session, 'utf8')

        # We have reconstructed a client, let's send a ping and see if we are
        # successful.
        try:
            client._request('ping')
        except python_freeipa.exceptions.Unauthorized as e:
            return None
        return client
    return None

# Attempt to obtain an administrative IPA session from config values.
#
# NOTE: You *MUST* check the result of this function every time you call it.
def maybe_ipa_admin_session(app):
    admin_user = app.config['FREEIPA_ADMIN_USER']
    admin_pass = app.config['FREEIPA_ADMIN_PASSWORD']
    client = Client(
        app.config['FREEIPA_SERVER'],
        verify_ssl=app.config['FREEIPA_CACERT'])
    try:
        client.login(admin_user, admin_pass)
        client._request('ping')
    except python_freeipa.exceptions.Unauthorized as e:
        return None
    return client


# Attempt to log in to an IPA server.
#
# On a successful login, we will encrypt the session token and put it in the
# user's session, returning the client handler to the caller.
#
# On an unsuccessful login, we'll set a flash and return None.
#
# TODO: Add some logging or maybe return something more useful on invalid login.
#       It will be useful to determine between "can't log in because the server
#       is broken" vs "can't log in because user gave a bad password"
#       We do catch and flash on expired password, though.
def maybe_ipa_login(app, username, password):
    client = Client(
        app.config['FREEIPA_SERVER'],
        verify_ssl=app.config['FREEIPA_CACERT'])

    auth = None

    try:
        auth = client.login(username, password)
    except python_freeipa.exceptions.PasswordExpired as e:
        flash(
            'Password expired. Please <a href="/password-reset">reset it</a>.',
            'red')
        return None
    except python_freeipa.exceptions.Unauthorized as e:
        flash(str(e), 'red')
        return None

    if auth and auth.logged_in:
        fernet = Fernet(app.config['FERNET_SECRET'])
        encrypted_session = fernet.encrypt(
            bytes(client._session.cookies['ipa_session'], 'utf8'))
        session['securitas_session'] = encrypted_session
        # Also store the username. Don't use it for anything sensitive, but
        # it's useful for simple redirects, etc.
        session['securitas_username_insecure'] = username
        return client

    return None
