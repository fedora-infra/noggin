from noggin.representation import Representation


class Group(Representation):

    ATTR_MAP = {
        "name": "cn",
        "description": "description",
        "members": "member_user",
        "sponsors": "membermanager_user",
        "url": "fasurl",
        "irc_channel": "fasircchannel",
        "mailing_list": "fasmailinglist",
    }
    ATTR_LISTS = ["members", "sponsors", "url"]

    pkey = "name"
    ipa_object = "group"

    @property
    def dn(self):
        if 'dn' in self.raw:
            return self.raw['dn']
        return None
