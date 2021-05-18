import random

import python_freeipa
from cryptography.fernet import Fernet
from python_freeipa.client_meta import ClientMeta as IPAClient
from python_freeipa.exceptions import BadRequest, ValidationError
from requests import RequestException


class Client(IPAClient):
    """
    Subclass the official client to add missing methods that we need.

    TODO: send this upstream.
    """

    def ping(self):
        """
        Checks that the server is alive.
        """
        return self._request("ping")

    def otptoken_sync(self, user, password, first_code, second_code, token=None):
        """
        Sync an otptoken for a user.

        :param user: the user to sync the token for
        :type user: string
        :param password: the user's password
        :type password: string
        :param first_code: the first OTP token
        :type first_code: string
        :param second_code: the second OTP token
        :type second_code: string
        :param token: the token description (optional)
        :type token: string
        """
        data = {
            'user': user,
            'password': password,
            'first_code': first_code,
            'second_code': second_code,
            'token': token,
        }
        url = "https://" + self._host + "/ipa/session/sync_token"
        try:
            response = self._session.post(url=url, data=data, verify=self._verify_ssl)
            if response.ok and "Token sync rejected" not in response.text:
                return response
            else:
                raise BadRequest(
                    message="The username, password or token codes are not correct."
                )
        except RequestException:
            raise BadRequest(message="Something went wrong trying to sync OTP token.")

    def fasagreement_find(self, **kwargs):
        """
        Search agreements
        """
        data = self._request('fasagreement_find', params=kwargs)
        return data['result']

    def fasagreement_add(self, agreement, **kwargs):
        """
        Add a new agreement
        :param agreement: Agreement name.
        :type agreement: string
        """
        data = self._request('fasagreement_add', agreement, kwargs)
        return data['result']

    def fasagreement_del(self, agreement, **kwargs):
        """
        Delete an agreement
        :param agreement: Agreement name.
        :type agreement: string
        """
        return self._request('fasagreement_del', agreement, kwargs)

    def fasagreement_add_user(self, agreement, **kwargs):
        """
        Add a user to an agreement
        :param agreement: Agreement name.
        :type agreement: string
        """
        data = self._request('fasagreement_add_user', agreement, kwargs)
        return data['result']

    def fasagreement_add_group(self, agreement, **kwargs):
        """
        Add a group to an agreement
        :param agreement: Agreement name.
        :type agreement: string
        """
        data = self._request('fasagreement_add_group', agreement, kwargs)
        return data['result']

    def fasagreement_remove_group(self, agreement, **kwargs):
        """
        Remove a group from an agreement
        :param agreement: Agreement name.
        :type agreement: string
        """
        data = self._request('fasagreement_remove_group', agreement, kwargs)
        return data['result']

    def fasagreement_disable(self, agreement, **kwargs):
        """
        Disable an agreement
        """
        self._request('fasagreement_disable', agreement, kwargs)


def raise_on_failed(result):
    failed = result.get("failed", {})
    num_failed = sum(
        sum(len(failures) for failures in object_types.values())
        for object_types in failed.values()
    )
    if num_failed == 0:
        return  # no actual failure
    raise ValidationError(failed)


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
    encrypted_session = session.get('noggin_session', None)
    server_hostname = session.get('noggin_ipa_server_hostname', None)
    if encrypted_session and server_hostname:
        fernet = Fernet(app.config['FERNET_SECRET'])
        ipa_session = fernet.decrypt(encrypted_session)
        client = Client(server_hostname, verify_ssl=app.config['FREEIPA_CACERT'])
        client._current_host = server_hostname
        client._session.cookies['ipa_session'] = str(ipa_session, 'utf8')

        # We have reconstructed a client, let's send a ping and see if we are
        # successful.
        try:
            ping = client.ping()
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
def maybe_ipa_login(app, session, username, userpassword):
    # A session token is bound to a particular server, so we store the server
    # in the session and just always use that. Flask sessions are signed, so we
    # are safe in later assuming that the server hostname cookie has not been
    # altered.
    chosen_server = random.choice(app.config['FREEIPA_SERVERS'])
    client = Client(chosen_server, verify_ssl=app.config['FREEIPA_CACERT'])

    auth = client.login(username, userpassword)

    if auth and auth.logged_in:
        fernet = Fernet(app.config['FERNET_SECRET'])
        encrypted_session = fernet.encrypt(
            bytes(client._session.cookies['ipa_session'], 'utf8')
        )
        session['noggin_session'] = encrypted_session
        session['noggin_ipa_server_hostname'] = chosen_server
        session['noggin_username'] = username
        return client

    return None
