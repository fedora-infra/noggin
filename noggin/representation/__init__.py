class Representation:

    ATTR_MAP = {}
    ATTR_LISTS = []

    def __init__(self, raw):
        self.raw = raw

    def _attr(self, attr):
        if attr in self.raw and len(self.raw[attr]) > 0:
            return self.raw[attr][0]
        return None

    def _attrlist(self, attr):
        if attr in self.raw:
            return self.raw[attr]
        return []

    def __getattr__(self, key):
        try:
            ipa_key = self.ATTR_MAP[key]
        except KeyError:
            raise AttributeError(key)
        if key in self.ATTR_LISTS:
            return self._attrlist(ipa_key)
        else:
            return self._attr(ipa_key)

    def __iter__(self):
        yield from self.ATTR_MAP.keys()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.raw == other.raw

    def diff_fields(self, other):
        """
        Compares two instances of the same class, and returns the properties
        with values that are different
        """
        if not isinstance(other, self.__class__):
            raise ValueError(
                f"Can't diff a {self.__class__.__name__} instance against a "
                f"{other.__class__.__name__} instance"
            )

        return [key for key in self if getattr(self, key) != getattr(other, key)]
