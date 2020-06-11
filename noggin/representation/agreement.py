import re

from .base import Representation


NOT_ASCII_RE = re.compile(r"\W")


class Agreement(Representation):

    attr_names = {
        "name": "cn",
        "enabled": "ipaenabledflag",
        "description": "description",
        "users": "memberuser_user",
        "groups": "member_group",
        "uniqueid": "ipauniqueid",
    }
    attr_types = {
        "users": "list",
        "groups": "list",
        "enabled": "bool",
    }
    pkey = "name"
    ipa_object = "fasagreement"

    @property
    def slug(self):
        return NOT_ASCII_RE.sub("", self.name)
