from cryptography.fernet import Fernet
import python_freeipa
from python_freeipa.client_legacy import ClientLegacy as IPAClient
from python_freeipa.exceptions import ValidationError
import random


def parse_group_management_error(data):
    """
    An extension of freeipa's function to handle membermanagers.

    TODO: send this upstream.
    """
    failed = data['failed']
    targets = ('member', 'membermanager')
    for target in targets:
        if target in failed and (failed[target]['group'] or failed[target]['user']):
            raise ValidationError(failed)


class Client(IPAClient):
    """
    Subclass the official client to add a missing method that we need.

    TODO: send this upstream.
    """

    def group_add_member_manager(
        self, group, users=None, groups=None, skip_errors=False, **kwargs
    ):
        """
        Add member managers to a group.

        :param group: Group name.
        :param users: Users to add.
        :type users: string or list
        :param groups: Groups to add.
        :type groups: string or list
        :param skip_errors: Skip processing errors.
        :type skip_errors: bool
        """
        params = {'all': True, 'raw': True, 'user': users, 'group': groups}
        params.update(kwargs)
        data = self._request('group_add_member_manager', group, params)
        if not skip_errors:
            parse_group_management_error(data)
        return data['result']


    def pwpolicy_mod(
        self, group, krbminpwdlife=None, **kwargs
    ):
        """
        Set the password time policy

        :param group: Group name.
        :param krbminpwdlife: The minimum password lifetime
        """
        params = {'all': True, 'raw': True, 'krbminpwdlife': krbminpwdlife}
        params.update(kwargs)
        data = self._request('pwpolicy_mod', group, params)
        return data['result']


# Construct an IPA client from app config, but don't attempt to log in with it
# or to form a session of any kind with it. This is useful for one-off cases
# like password resets where a session isn't actually required.
def untouched_ipa_client(app):
    return Client(
        random.choice(app.config['FREEIPA_SERVERS']),
        verify_ssl=app.config['FREEIPA_CACERT'],
    )


# Attempt to obtain an IPA session from a cookie.
#
# If we are given a token as a cookie in the request, decrypt it and see if we
# are left with a valid IPA session.
#
# NOTE: You *MUST* check the result of this function every time you call it.
# It will be None if no session was provided or was provided but invalid.
def maybe_ipa_session(app, session):
    encrypted_session = session.get('securitas_session', None)
    server_hostname = session.get('securitas_ipa_server_hostname', None)
    if encrypted_session and server_hostname:
        fernet = Fernet(app.config['FERNET_SECRET'])
        ipa_session = fernet.decrypt(encrypted_session)
        client = Client(server_hostname, verify_ssl=app.config['FREEIPA_CACERT'])
        client._session.cookies['ipa_session'] = str(ipa_session, 'utf8')

        # We have reconstructed a client, let's send a ping and see if we are
        # successful.
        try:
            ping = client._request('ping')
            client.ipa_version = ping['summary']
        except python_freeipa.exceptions.Unauthorized:
            return None
        # If there's any other kind of exception, we let it propagate up for the
        # controller (and, more practically, @with_ipa) to handle.
        return client
    return None


# Attempt to log in to an IPA server.
#
# On a successful login, we will encrypt the session token and put it in the
# user's session, returning the client handler to the caller.
#
# On an unsuccessful login, we'll let the exception bubble up.
def maybe_ipa_login(app, session, username, password):
    # A session token is bound to a particular server, so we store the server
    # in the session and just always use that. Flask sessions are signed, so we
    # are safe in later assuming that the server hostname cookie has not been
    # altered.
    chosen_server = random.choice(app.config['FREEIPA_SERVERS'])
    client = Client(chosen_server, verify_ssl=app.config['FREEIPA_CACERT'])

    auth = client.login(username, password)

    if auth and auth.logged_in:
        fernet = Fernet(app.config['FERNET_SECRET'])
        encrypted_session = fernet.encrypt(
            bytes(client._session.cookies['ipa_session'], 'utf8')
        )
        session['securitas_session'] = encrypted_session
        session['securitas_ipa_server_hostname'] = chosen_server
        session['securitas_username'] = username
        return client

    return None
