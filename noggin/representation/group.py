from .base import Representation


class Group(Representation):

    attr_names = {
        "name": "cn",
        "description": "description",
        "members": "member_user",
        "sponsors": "membermanager_user",
        "urls": "fasurl",
        "irc_channel": "fasircchannel",
        "mailing_list": "fasmailinglist",
    }
    attr_types = {
        "members": "list",
        "sponsors": "list",
        "urls": "list",
    }
    pkey = "name"
    ipa_object = "group"
