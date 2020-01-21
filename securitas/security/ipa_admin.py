from functools import wraps

from python_freeipa.client_legacy import ClientLegacy
import random


class IPAAdmin(object):

    __WRAPPED_METHODS = ("user_add", "user_del", "group_add", "group_del")

    def __init__(self, app):
        self.__username = app.config['FREEIPA_ADMIN_USER']
        self.__password = app.config['FREEIPA_ADMIN_PASSWORD']
        app.config['FREEIPA_ADMIN_USER'] = '***'
        app.config['FREEIPA_ADMIN_PASSWORD'] = '***'  # nosec
        self.__app = app

    # Attempt to obtain an administrative IPA session
    def __maybe_ipa_admin_session(self):
        self.__client = ClientLegacy(
            random.choice(self.__app.config['FREEIPA_SERVERS']),
            verify_ssl=self.__app.config['FREEIPA_CACERT'],
        )
        self.__client.login(self.__username, self.__password)
        self.__client._request('ping')
        return self.__client

    def __wrap_method(self, method_name):
        @wraps(getattr(ClientLegacy, method_name))
        def wrapper(*args, **kwargs):
            ipa = self.__maybe_ipa_admin_session()
            ipa_method = getattr(ipa, method_name)
            res = ipa_method(*args, **kwargs)
            ipa.logout()
            return res

        return wrapper

    def __getattr__(self, name):
        if name in self.__WRAPPED_METHODS:
            return self.__wrap_method(name)
        raise AttributeError(name)
