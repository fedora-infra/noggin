from .base import Representation


class User(Representation):

    attr_names = {
        "username": "uid",
        "firstname": "givenname",
        "lastname": "sn",
        "commonname": "cn",
        "displayname": "displayname",
        "gecos": "gecos",
        "mail": "mail",
        "sshpubkeys": "ipasshpubkey",
        "last_password_change": "krblastpwdchange",
        "agreements": "memberof_fasagreement",
        "groups": "memberof_group",
        "timezone": "fastimezone",
        "locale": "faslocale",
        "ircnick": "fasircnick",
        "gpgkeys": "fasgpgkeyid",
        "github": "fasgithubusername",
        "gitlab": "fasgitlabusername",
        "rhbz_mail": "fasrhbzemail",
        "website_url": "faswebsiteurl",
        "status_note": "fasstatusnote",
        "creation_time": "fascreationtime",
        "is_private": "fasisprivate",
        "pronouns": "faspronoun",
    }
    attr_types = {
        "sshpubkeys": "list",
        "ircnick": "list",
        "gpgkeys": "list",
        "groups": "list",
        "agreements": "list",
        "is_private": "bool",
    }
    pkey = "username"
    ipa_object = "user"

    @property
    def name(self):
        return self.displayname or self.gecos or self.commonname

    @property
    def locked(self):
        # Unlike the others nsAccountLock is not a list.
        return self.raw.get("nsaccountlock", False)

    def anonymize(self):
        not_hidden = [
            "username",
            "mail",
            "last_password_change",
            "agreements",
            "groups",
            "status_note",
            "creation_time",
            "is_private",
        ]
        for attr_name in self.attr_names:
            if attr_name in not_hidden:
                continue
            setattr(self, attr_name, None)
