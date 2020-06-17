from noggin.representation import Representation


class User(Representation):

    ATTR_MAP = {
        "username": "uid",
        "firstname": "givenname",
        "lastname": "sn",
        "mail": "mail",
        "sshpubkeys": "ipasshpubkey",
        "timezone": "fastimezone",
        "locale": "faslocale",
        "ircnick": "fasircnick",
        "gpgkeys": "fasgpgkeyid",
        "groups": "memberof_group",
        "github": "fasgithubusername",
        "gitlab": "fasgitlabusername",
        "rhbz_mail": "fasrhbzemail",
        "website_url": "faswebsiteurl",
        "last_password_change": "krblastpwdchange",
        "agreements": "memberof_fasagreement",
    }
    ATTR_LISTS = ["sshpubkeys", "ircnick", "gpgkeys", "groups", "agreements"]

    pkey = "username"
    ipa_object = "user"

    @property
    def name(self):
        if 'displayname' in self.raw:
            return self._attr('displayname')
        if 'gecos' in self.raw:
            return self._attr('gecos')
        if 'cn' in self.raw:
            return self._attr('cn')
        return None
