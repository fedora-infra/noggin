import hashlib
from functools import wraps
from flask import abort, flash, g, redirect, url_for
import python_freeipa

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
                g.ipa = ipa
                return f(*args, **kwargs, ipa=ipa)
            flash('Please log in to continue.', 'orange')
            return redirect(url_for('root'))
        return fn
    return decorator

def group_or_404(ipa, groupname):
    try:
        return ipa.group_show(groupname)
    except python_freeipa.exceptions.NotFound:
        abort(404)

def user_or_404(ipa, username):
    try:
        return ipa.user_show(username)
    except python_freeipa.exceptions.NotFound:
        abort(404)
