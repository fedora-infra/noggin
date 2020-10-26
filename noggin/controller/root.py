import python_freeipa
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import _
from flask_healthz import HealthError

from noggin.app import ipa_admin
from noggin.form.login_user import LoginUserForm
from noggin.form.register_user import RegisterUserForm
from noggin.representation.group import Group
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_session
from noggin.utility.controllers import with_ipa
from noggin.utility.forms import handle_form_errors

from . import blueprint as bp
from .authentication import handle_login_form
from .registration import handle_register_form


@bp.route('/', methods=['GET', 'POST'])
def root():
    ipa = maybe_ipa_session(current_app, session)
    username = session.get('noggin_username')
    if ipa and username:
        return redirect(url_for('.user', username=username))

    # Kick any non-authed user back to the login form.

    activetab = request.args.get("tab", "login")

    register_form = RegisterUserForm(prefix="register")
    login_form = LoginUserForm(prefix="login")

    if login_form.validate_on_submit():
        with handle_form_errors(login_form):
            return handle_login_form(login_form)

    if register_form.validate_on_submit():
        if not current_app.config["REGISTRATION_OPEN"]:
            flash(_("Registration is closed at the moment."), "warning")
            return redirect(url_for('.root'))
        with handle_form_errors(register_form):
            return handle_register_form(register_form)

    return render_template(
        'index.html',
        register_form=register_form,
        login_form=login_form,
        activetab=activetab,
    )


@bp.route('/logout')
def logout():
    """Log the user out."""
    # Don't use the with_ipa() decorator, otherwise anonymous users visiting this endpoint will be
    # asked to login to then be logged out.
    try:
        ipa = maybe_ipa_session(current_app, session)
    except python_freeipa.exceptions.FreeIPAError:
        # Not much we can do here, proceed to logout and it may help solve the issue.
        ipa = None
    if ipa:
        ipa.logout()
    session.clear()
    return redirect(url_for('.root'))


@bp.route('/search/json')
@with_ipa()
def search_json(ipa):
    username = request.args.get('username')
    groupname = request.args.get('group')

    res = []

    if username:
        users_ = [
            User(u)
            for u in ipa.user_find(username, fasuser=True, sizelimit=10)['result']
        ]

        for user_ in users_:
            res.append(
                {
                    'uid': user_.username,
                    'cn': user_.name,
                    'url': url_for(".user", username=user_.username),
                }
            )

    if groupname:
        groups_ = [
            Group(g)
            for g in ipa.group_find(groupname, fasgroup=True, sizelimit=10)['result']
        ]
        for group_ in groups_:
            res.append(
                {
                    'cn': group_.name,
                    'description': group_.description,
                    'url': url_for(".group", groupname=group_.name),
                }
            )

    return jsonify(res)


def liveness():
    pass


def readiness():
    try:
        ipa_admin.ping()
    except Exception:
        raise HealthError("Can't connect to the FreeIPA Server")
