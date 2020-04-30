import hashlib
from functools import wraps
from contextlib import contextmanager

from flask import abort, flash, g, redirect, url_for, session, Markup
from flask_babel import lazy_gettext as _
import python_freeipa

from noggin import app
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_session


def gravatar(email, size):
    return (
        app.config["AVATAR_SERVICE_URL"]
        + "avatar/"
        + hashlib.md5(email.lower().encode('utf8')).hexdigest()  # nosec
        + "?s="
        + str(size)
        + "&d="
        + app.config["AVATAR_DEFAULT_TYPE"]
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


def require_self(f):
    """Require the logged-in user to be the user that is currently being edited"""

    @wraps(f)
    def fn(*args, **kwargs):
        try:
            username = kwargs["username"]
        except KeyError:
            abort(
                500,
                "The require_self decorator only works on routes that have 'username' "
                "as a component.",
            )
        if session.get('noggin_username') != username:
            flash('You do not have permission to edit this account.', 'danger')
            return redirect(url_for('user', username=username))
        return f(*args, **kwargs)

    return fn


def group_or_404(ipa, groupname):
    group = ipa.group_find(cn=groupname, fasgroup=True)['result']
    if not group:
        abort(404, _('Group %(groupname)s could not be found.', groupname=groupname))
    else:
        return group[0]


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
    """Handle form errors by raising exceptions.

    The point of this context manager is to let controller developers create form errors by raising
    exceptions instead of setting variables. This is particularly useful when you are making
    multiple API calls in a row and handling exceptions separately: instead of doing nested
    ``try..except..else`` statements they would have non-nested code raising exceptions.

    For example, without this function you would have something similar to::

        if form.validate_on_submit():
            try:
                api_call_1()
            except UserError as e:
                form.user.errors.append(e.msg)
            else:
                try:
                    api_call_2()
                except PasswordError as e:
                    form.password.errors.append(e.msg)
                else:
                    try:
                        api_call_3()
                    except GenericError as e:
                        form.errors['non_field_errors'] = [e.msg]
                    else:
                        flash("Success!")
                        return redirect("/")
        return render_template(..., form=form)

    Every API call causes an additional level of nesting because the code must fall through the
    initial ``if`` statement to reach the ``render_template`` call. With this function this could be
    rewritten as::

        if form.validate_on_submit():
            with handle_form_errors(form):
                try:
                    api_call_1()
                except UserError as e:
                    raise FormError("user", e.msg)
                try:
                    api_call_2()
                except PasswordError as e:
                    raise FormError("password", e.msg)
                try:
                    api_call_3()
                except GenericError as e:
                    raise FormError("non_field_errors", e.msg)
                flash("Success!")
                return redirect("/")
        return render_template(..., form=form)

    This code does not nest more on each API call, which is (arguably) clearer as the number of
    necessary API call increases.

    Args: form (wtforms.Form): The form that errors should be stored to
    """
    try:
        yield
    except FormError as e:
        e.populate_form(form)


def undo_button(form_action, submit_name, submit_value, hidden_tag):
    """return an undo button html snippet as a string, to be used in flash messages"""

    undo_text = _("Undo")

    template = f"""
    <span class='ml-auto' id="flashed-undo-button">
        <form action="{form_action}" method="post">
            {hidden_tag}
            <button type="submit" class="btn btn-outline-success btn-sm"
             name="{submit_name}" value="{submit_value}">
                {undo_text}
            </button>
        </form>
    </span>"""
    return Markup(template)
