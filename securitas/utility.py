import collections
import hashlib
from functools import wraps
from flask import flash, redirect, url_for

from securitas.security.ipa import maybe_ipa_session

def gravatar(email, size):
    return "https://www.gravatar.com/avatar/" + hashlib.md5(
        email.lower().encode('utf8')).hexdigest() + "?s=" + str(size) # nosec

# A wrapper that will give us 'ipa' if it exists, or bump the user back to /
# with a message telling them to log in.
def with_ipa(app, session):
    def decorator(f):
        @wraps(f)
        def fn(*args, **kwargs):
            ipa = maybe_ipa_session(app, session)
            if ipa:
                return f(*args, **kwargs, ipa=ipa)
            flash('Please log in to continue.', 'orange')
            return redirect(url_for('root'))
        return fn
    return decorator

# We invent a fake "Maybe" monad here, but really the goal is to get a pretty
# DSL to use in templates, so we can do things like:
#
# {{ Get(user).get('uid').get(0).or_else('email').get(0).otherwise('Nope!').final }}
class Get(object):
    def __init__(self, clxn, top=None):
        self._clxn = clxn
        self.final = self._clxn
        if top:
            self.top = top.top
        else:
            self.top = self

    # If the final value we land on is None, hop back to the
    # beginning and try again.
    def or_else(self, idx, default=None):
        if self.final is None:
            return self.top.get(idx, default)
        else:
            return Get(self.final)

    # Just an alias for the constructor to make a pretty DSL:
    # {{ Get(user).get('uid').get(0).or_else('email').get(0).otherwise('Unknown').final }}
    def otherwise(self, default):
        return Get(default)

    def get(self, idx, default=None):
        if isinstance(self._clxn, collections.Mapping):
            return Get(self._clxn.get(idx, default), self)
        if '__getitem__' in dir(self._clxn):
            try:
                return Get(self._clxn[idx], self)
            except IndexError:
                return Get(default, self)
        # We got something that doesn't seem to be iterable.
        # Maybe a None. Return the last default of the chain, but still wrapped in
        # Get.
        return Get(default, self)
