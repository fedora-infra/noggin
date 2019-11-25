import collections

# We invent a fake "Maybe" monad here, but really the goal is to get a pretty
# DSL to use in templates, so we can do things like:
#
# {{ Get(user).get('uid').get(0).or_else('email').get(0).otherwise('Nope!').final }}
#
# Except we go even further and let you use [] index notation.
class Get(object):
    """
    Some pretty wrappers for chaining getters of indexable collections.
    Doctests:

    >>> c = {'tomatoes': {'tasty': False}, 'foo': 'bar'}

    This is the pretty indexing notation:
    >>> Get(c)['tomatoes']['tasty'].final
    False

    But it's the same as this:
    >>> Get(c).get('tomatoes').get('tasty').final
    False

    You can specify your default along in .get():
    >>> Get(c).get('tomatoes', 'default').final
    {'tasty': False}
    >>> Get(c).get('monkies', 'default').final
    'default'

    Or do so at the end:
    >>> Get(c).get('tomatoes').otherwise('default').final
    {'tasty': False}
    >>> Get(c).get('monkies').otherwise('default').final
    'default'

    It also works with index notation:
    >>> Get(c)['tomatoes'].otherwise('default').final
    {'tasty': False}
    >>> Get(c)['monkies'].otherwise('default').final
    'default'

    More complex chaining works too. When using verbose notation, the
    `or_else` method will start a chain back at the original object
    (c in this case).

    This is useful to explore multiple paths before giving up:
    >>> Get(c).get('tomatoes').get('red').or_else('tomatoes').get('tasty').final
    False

    The index notation variant is called `rather` and is exposed as a property
    to avoid needing parentheses:
    >>> Get(c)['tomatoes']['red'].rather['tomatoes']['tasty'].final
    False

    And of course we can still specify a default:
    >>> Get(c)['tomatoes']['red'].rather['tomatoes']['spicy'].otherwise('default').final
    'default'

    This shows what happens if we fall all the way through:
    >>> Get(c)['asdf'].rather['bar']['zzz'].otherwise('haha').final
    'haha'

    This is the same, but with no default at all. We get None back at the end:
    >>> Get(c)['tomatoes']['tastyjj'].rather['foo']['bar'].final

    If we had specified a default, we would have gotten it back, though:
    >>> Get(c)['tomatoes']['tastyjj'].rather['foo']['bar'].otherwise('fishes').final
    'fishes'
    """
    def __init__(self, clxn, top=None):
        self._clxn = clxn
        if top:
            self.top = top.top
        else:
            self.top = self

        # Some pretty names for the above
        self.final = self._clxn

    # If the final value we land on is None, hop back to the
    # beginning and try again.
    def or_else(self, idx, default=None):
        if self.final is None:
            return self.top.get(idx, default)
        else:
            return Get(self.final)

    # If we got None back, default to the value given here.
    def otherwise(self, default):
        if self._clxn is None:
            return Get(default)
        else:
            return self

    @property
    def rather(self):
        if self._clxn is None:
            return self.top
        else:
            return Get(self._clxn)

    def get(self, idx, default=None):
        if isinstance(self._clxn, collections.Mapping):
            return Get(self._clxn.get(idx, default), self)
        if '__getitem__' in dir(self._clxn):
            try:
                return Get(self._clxn[idx], self)
            except (IndexError, TypeError):
                return Get(default, self)

        return Get(self.final)

    # We can go a bit further:
    # {{ Get(user)['uid'][0].rather['email'][0].otherwise('some default').final }}
    def __getitem__(self, idx):
        return self.get(idx)

    # This makes using these in Jinja nicer, we can leave the .final off.
    def __str__(self):
        return self.final
