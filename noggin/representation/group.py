from noggin.representation import Representation


class Group(Representation):

    ATTR_MAP = {
        "name": "cn",
        "description": "description",
        "members": "member_user",
        "sponsors": "membermanager_user",
    }
    ATTR_LISTS = ["members", "sponsors"]

    @property
    def dn(self):
        if 'dn' in self.raw:
            return self.raw['dn']
        return None

    def __eq__(self, obj):
        return isinstance(obj, Group) and self.raw == obj.raw
