from datetime import datetime


def attr_to_str(value):
    if not value:
        return None
    return value[0]


def attr_to_list(value):
    return value or []


def attr_to_bool(value):
    if not value:
        return False
    return value[0] == "TRUE"


def attr_to_date(value):
    if value is None:
        return None
    dt = value[0]["__datetime__"]
    return datetime.strptime(dt, r"%Y%m%d%H%M%SZ")


CONVERTERS = {
    "str": attr_to_str,
    "list": attr_to_list,
    "bool": attr_to_bool,
    "date": attr_to_date,
}


class Representation:

    attr_names = {}
    attr_types = {}
    attr_options = {}
    pkey = None

    def __init__(self, raw):
        self.raw = raw

    def __getattr__(self, key):
        try:
            ipa_key = self.attr_names[key]
        except KeyError:
            raise AttributeError(key)
        attr_type = self.attr_types.get(key, "str")
        converter = CONVERTERS[attr_type]
        return converter(self.raw.get(ipa_key))

    def __iter__(self):
        yield from self.attr_names.keys()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.raw == other.raw

    def __hash__(self):
        return hash(self.dn)

    @property
    def dn(self):
        return self.raw.get("dn")

    @classmethod
    def get_ipa_pkey(cls):
        if cls.pkey is None:
            raise NotImplementedError
        try:
            return cls.attr_names[cls.pkey]
        except KeyError:
            raise NotImplementedError

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

    def as_dict(self):
        return {attr: getattr(self, attr) for attr in self.attr_names}

    def get_attr_option(self, attr):
        attr_to_options = self.attr_names.copy()
        attr_to_options.update(self.attr_options)
        return attr_to_options[attr]
