from noggin.representation import Representation


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

    pkey = "name"
    ipa_object = "fasagreement"
