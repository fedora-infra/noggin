import re

from noggin.representation import Representation


NOT_ASCII_RE = re.compile(r"\W")


class Agreement(Representation):

    ATTR_MAP = {
        "name": "cn",
        "enabled": "ipaenabledflag",
        "description": "description",
        "users": "memberuser_user",
        "groups": "member_group",
        "uniqueid": "ipauniqueid",
    }
    ATTR_LISTS = ["users", "groups"]
    ATTR_BOOLS = ["enabled"]

    pkey = "name"
    ipa_object = "fasagreement"

    @property
    def slug(self):
        return NOT_ASCII_RE.sub("", self.name)
