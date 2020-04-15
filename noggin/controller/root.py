from flask import render_template, request, redirect, url_for, session, jsonify

from noggin import app
from noggin.form.register_user import RegisterUserForm
from noggin.form.login_user import LoginUserForm
from noggin.representation.group import Group
from noggin.representation.user import User

from noggin.security.ipa import maybe_ipa_session
from noggin.utility import with_ipa, handle_form_errors

from .authentication import handle_login_form
from .registration import handle_register_form


@app.route('/', methods=['GET', 'POST'])
def root():
    ipa = maybe_ipa_session(app, session)
    username = session.get('noggin_username')
    if ipa and username:
        return redirect(url_for('user', username=username))

    # Kick any non-authed user back to the login form.

    activetab = request.args.get("tab", "login")

    register_form = RegisterUserForm(prefix="register")
    login_form = LoginUserForm(prefix="login")

    if login_form.validate_on_submit():
        with handle_form_errors(login_form):
            return handle_login_form(login_form)

    if register_form.validate_on_submit():
        with handle_form_errors(register_form):
            return handle_register_form(register_form)

    return render_template(
        'index.html',
        register_form=register_form,
        login_form=login_form,
        activetab=activetab,
    )


@app.route('/logout')
def logout():
    """Log the user out."""
    # Don't use the with_ipa() decorator, otherwise anonymous users visiting this endpoint will be
    # asked to login to then be logged out.
    ipa = maybe_ipa_session(app, session)
    if ipa:
        ipa.logout()
    session.clear()
    return redirect(url_for('root'))


@app.route('/search/json')
@with_ipa(app, session)
def search_json(ipa):
    username = request.args.get('username')
    groupname = request.args.get('group')

    res = []

    if username:
        users_ = [User(u) for u in ipa.user_find(username)['result']]

        for user_ in users_:
            res.append({'uid': user_.username, 'cn': user_.name})

    if groupname:
        groups_ = [Group(g) for g in ipa.group_find(groupname)['result']]
        for group_ in groups_:
            res.append({'cn': group_.name, 'description': group_.description})

    return jsonify(res)
