class Representation(object):
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
    
    def get_properties(self):
        """
        Returns a dict of all the properties defined above and their values
        """
        return {
            key: getattr(self, key)
            for key, value in self.__class__.__dict__.items()
            if isinstance(value, property)
        }

    def diff_fields(self, other):
        """
        Compares two instances of the User class, and returns the properties
        with values that are different
        """
        if not isinstance(other, self.__class__):
            raise ValueError(f"Can't diff a {self.__class__.__name__} instance against a {other.__class__.__name__} instance")

        return [
            key
            for key, value in self.get_properties().items()
            if value != other.get_properties()[key]
        ]
