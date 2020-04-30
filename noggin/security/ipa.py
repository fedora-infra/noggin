import random
from requests import RequestException

from cryptography.fernet import Fernet
import python_freeipa
from python_freeipa.client_legacy import ClientLegacy as IPAClient
from python_freeipa.exceptions import ValidationError, BadRequest


def parse_group_management_error(data):
    """
    An extension of freeipa's function to handle membermanagers.

    TODO: send this upstream.
    """
    try:
        failed = data['failed']
    except KeyError:
        return
    targets = ('member', 'membermanager')
    for target in targets:
        if target in failed and (failed[target]['group'] or failed[target]['user']):
            raise ValidationError(failed)


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

    def otptoken_add(
        self, ipatokenowner=None, ipatokenotpalgorithm=None, description=False
    ):
        """
        Add an otptoken for a user.

        :param ipatokenowner: the username
        :type ipatokenowner: string
        :param ipatokenotpalgorithm: the token algorithim
        :type ipatokenotpalgorithm: string
        :param description: the token's description.
        :type description: string
        """
        params = {
            'ipatokenowner': ipatokenowner,
            'ipatokenotpalgorithm': ipatokenotpalgorithm,
            'description': description,
        }
        data = self._request('otptoken_add', [], params)
        return data['result']

    def otptoken_mod(self, ipatokenuniqueid, ipatokendisabled=False):
        """
        Mod an otptoken for a user.

        :param ipatokenuniqueid: the unique id of the token
        :type ipatokenuniqueid: string
        :param ipatokendisabled: whether it should be disabled
        :type ipatokendisabled: boolean
        """
        params = {
            'ipatokenuniqueid': ipatokenuniqueid,
            'ipatokendisabled': ipatokendisabled,
        }
        data = self._request('otptoken_mod', [], params)
        return data['result']

    def otptoken_del(self, ipatokenuniqueid):
        """
        Mod an otptoken for a user.

        :param ipatokenuniqueid: the unique id of the token
        :type ipatokenuniqueid: string
        """
        params = {'ipatokenuniqueid': ipatokenuniqueid}
        data = self._request('otptoken_del', [], params)
        return data['result']

    def otptoken_find(self, ipatokenowner=None):
        """
        Find otptokens for a user.

        :param ipatokenowner: the username
        :type ipatokenowner: string
        """
        params = {'ipatokenowner': ipatokenowner}
        data = self._request('otptoken_find', [], params)
        return data['result']

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

    def batch(self, methods=None, raise_errors=True):
        """
        Make multiple ipa calls via one remote procedure call.

        :param methods: Nested Methods to execute.
        :type methods: dict
        :param skip_errors: Raise errors from RPC calls.
        :type skip_errors: bool
        """
        data = self._request('batch', methods)
        for idx, result in enumerate(data['results']):
            error = result['error']
            if error:
                exception = BadRequest(message=error, code=result['error_code'])
                if raise_errors:
                    raise exception
                else:
                    data['results'][idx] = exception
        return data

    def pwpolicy_add(
        self,
        group,
        krbminpwdlife=None,
        krbpwdminlength=None,
        cospriority=None,
        **kwargs
    ):
        """
        Create the password policy

        :param group: Group name.
        :param krbminpwdlife: The minimum password lifetime
        :param krbpwdminlength: The minimum password length
        """
        params = {
            'all': True,
            'raw': False,
            'krbminpwdlife': krbminpwdlife,
            'cospriority': cospriority,
            'krbpwdminlength': krbpwdminlength,
        }
        params.update(kwargs)
        data = self._request('pwpolicy_add', group, params)
        return data['result']

    def pwpolicy_mod(
        self, group=None, krbminpwdlife=None, krbpwdminlength=None, **kwargs
    ):
        """
        Create the password policy

        :param group: group name or None for the global policy
        :param krbminpwdlife: The minimum password lifetime
        :param krbpwdminlength: The minimum password length
        """
        params = {
            'all': True,
            'raw': False,
            'krbminpwdlife': krbminpwdlife,
            'krbpwdminlength': krbpwdminlength,
        }
        params.update(kwargs)
        data = self._request('pwpolicy_mod', group, params)
        return data['result']

    def pwpolicy_show(self, group=None, **kwargs):
        """
        Display information about a password policy.
        :param group: group name or None for the global policy
        :type group: string
        """
        params = {'all': True, 'raw': False}
        params.update(kwargs)
        data = self._request('pwpolicy_show', group, params)
        return data['result']

    # Stage user handling
    # Wow it's really time we moved to the autogenerated code...

    def stageuser_add(self, username, first_name, last_name, **kwargs):
        """
        Add a new stage user. Basically the same arguments as user_add.

        We only set the variables we use in noggin, it's too much of a pain to copy them all.
        """
        params = {'all': True, 'givenname': first_name, 'sn': last_name}
        args_mapping = {
            "full_name": "cn",
            "user_password": "userpassword",
            "login_shell": "loginshell",
        }
        for arg_name, arg_value in kwargs.items():
            if arg_name in args_mapping:
                params[args_mapping[arg_name]] = arg_value
            else:
                params[arg_name] = arg_value

        data = self._request('stageuser_add', username, params)
        return data['result']

    def stageuser_mod(self, username, **kwargs):
        """
        Add a new stage user. Basically the same arguments as user_add.

        We only set the variables we use in noggin, it's too much of a pain to copy them all.
        """
        params = {'all': True}
        args_mapping = {
            "first_name": "givenname",
            "last_name": "sn",
            "full_name": "cn",
            "user_password": "userpassword",
            "login_shell": "loginshell",
        }
        for arg_name, arg_value in kwargs.items():
            if arg_name in args_mapping:
                # No need to check for coverage here, it's only used in the unit tests.
                params[args_mapping[arg_name]] = arg_value  # pragma: no cover
            else:
                params[arg_name] = arg_value

        data = self._request('stageuser_mod', username, params)
        return data['result']

    def stageuser_show(self, username):
        """
        Display information about a stage user.
        :param username: User login.
        :type username: string
        """
        data = self._request('stageuser_show', username, {'all': True, 'raw': False})
        return data['result']

    def stageuser_del(self, username, skip_errors=False):
        """
        Delete a stage user.

        :param username: User login.
        :type username: string
        :param skip_errors: Continuous mode: Don't stop on errors.
        :type skip_errors: bool
        """
        params = {'continue': skip_errors}
        return self._request('stageuser_del', username, params)

    def stageuser_activate(self, username, **kwargs):
        """
        Activate a stage user.
        :param username: User login.
        :type username: string
        """
        params = {'all': True}
        params.update(kwargs)
        data = self._request('stageuser_activate', username, params)
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
        session['noggin_session'] = encrypted_session
        session['noggin_ipa_server_hostname'] = chosen_server
        session['noggin_username'] = username
        return client

    return None
