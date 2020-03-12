from noggin.representation import Representation


class Group(Representation):
    @property
    def name(self):
        return self._attr('cn')

    @property
    def description(self):
        return self._attr('description')

    @property
    def members(self):
        return self._attrlist('member_user')

    @property
    def sponsors(self):
        return self._attrlist('membermanager_user')

    @property
    def dn(self):
        if 'dn' in self.raw:
            return self.raw['dn']
        return None

    def __eq__(self, obj):
        return isinstance(obj, Group) and self.raw == obj.raw
