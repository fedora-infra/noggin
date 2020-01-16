from python_freeipa import Client
import random


class IPAAdmin(object):
    def __init__(self, app):
        self.__username = app.config['FREEIPA_ADMIN_USER']
        self.__password = app.config['FREEIPA_ADMIN_PASSWORD']
        app.config['FREEIPA_ADMIN_USER'] = '***'
        app.config['FREEIPA_ADMIN_PASSWORD'] = '***'  # nosec
        self.__app = app

    # Attempt to obtain an administrative IPA session
    def __maybe_ipa_admin_session(self):
        self.__client = Client(
            random.choice(self.__app.config['FREEIPA_SERVERS']),
            verify_ssl=self.__app.config['FREEIPA_CACERT'],
        )
        self.__client.login(self.__username, self.__password)
        self.__client._request('ping')
        return self.__client

    def user_add(self, *args, **kwargs):
        ipa = self.__maybe_ipa_admin_session()
        res = ipa.user_add(*args, **kwargs)
        ipa.logout()
        return res

    def user_del(self, *args, **kwargs):
        ipa = self.__maybe_ipa_admin_session()
        res = ipa.user_del(*args, **kwargs)
        ipa.logout()
        return res
