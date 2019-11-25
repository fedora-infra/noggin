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
