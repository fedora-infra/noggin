import hashlib
from functools import wraps
from contextlib import contextmanager

from flask import abort, flash, g, redirect, url_for
import python_freeipa

from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_session


def gravatar(email, size):
    return (
        "https://seccdn.libravatar.org/avatar/"
        + hashlib.md5(email.lower().encode('utf8')).hexdigest()  # nosec
        + "?s="
        + str(size)
        + "&d=robohash"
    )


# A wrapper that will give us 'ipa' if it exists, or bump the user back to /
# with a message telling them to log in.
def with_ipa(app, session):
    def decorator(f):
        @wraps(f)
        def fn(*args, **kwargs):
            ipa = maybe_ipa_session(app, session)
            if ipa:
                g.ipa = ipa
                g.current_user = User(g.ipa.user_find(whoami=True)['result'][0])
                return f(*args, **kwargs, ipa=ipa)
            flash('Please log in to continue.', 'warning')
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


class FormError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message

    def populate_form(self, form):
        try:
            field = getattr(form, self.field)
        except AttributeError:
            # probably non_field_errors
            if self.field not in form.errors:
                form.errors[self.field] = []
            error_list = form.errors[self.field]
        else:
            error_list = field.errors
        error_list.append(self.message)


@contextmanager
def handle_form_errors(form):
    try:
        yield
    except FormError as e:
        e.populate_form(form)
