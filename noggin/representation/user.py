from .base import CONVERTERS, Representation


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
        "krbname": "krbcanonicalname",
        "roles": "memberof_role",
    }
    attr_types = {
        "sshpubkeys": "list",
        "ircnick": "list",
        "gpgkeys": "list",
        "groups": "list",
        "agreements": "list",
        "is_private": "bool",
        "pronouns": "list",
        "creation_time": "date",
        "last_password_change": "date",
        "roles": "list",
    }
    attr_options = {
        "firstname": "o_givenname",
        "lastname": "o_sn",
        "mail": "o_mail",
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

    @property
    def groups(self):
        """Merge the direct and the indirect groups."""
        direct_groups = self.raw.get("memberof_group", [])
        indirect_groups = self.raw.get("memberofindirect_group", [])
        return CONVERTERS["list"](direct_groups + indirect_groups)

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
