from .base import Representation


class User(Representation):

    attr_names = {
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
        "displayname": "displayname",
        "gecos": "gecos",
        "commonname": "cn",
        "status_note": "fasstatusnote",
    }
    attr_types = {
        "sshpubkeys": "list",
        "ircnick": "list",
        "gpgkeys": "list",
        "groups": "list",
        "agreements": "list",
    }
    pkey = "username"
    ipa_object = "user"

    @property
    def name(self):
        return self.displayname or self.gecos or self.commonname
