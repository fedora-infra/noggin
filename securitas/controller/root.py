from flask import render_template, request, redirect, url_for, session, jsonify

from securitas import app
from securitas.form.register_user import RegisterUserForm
from securitas.form.login_user import LoginUserForm
from securitas.representation.group import Group
from securitas.representation.user import User
from securitas.security.ipa import maybe_ipa_session
from securitas.utility import with_ipa


@app.route('/')
def root():
    ipa = maybe_ipa_session(app, session)
    username = session.get('securitas_username')
    if ipa and username:
        return redirect(url_for('user', username=username))
    # Kick any non-authed user back to the login form.
    register_form = RegisterUserForm()
    login_form = LoginUserForm()
    return render_template(
        'index.html', register_form=register_form, login_form=login_form
    )


@app.route('/search/json')
@with_ipa(app, session)
def search_json(ipa):
    username = request.args.get('username')
    groupname = request.args.get('group')

    res = []

    if username:
        users_ = [User(u) for u in ipa.user_find(username)['result']]

        for user_ in users_:
            uid = user_.username
            cn = user_.name
            if uid is not None:
                # If the cn is None, who cares?
                res.append({'uid': uid, 'cn': cn})

    if groupname:
        groups_ = [Group(g) for g in ipa.group_find(groupname)['result']]
        for group_ in groups_:
            cn = group_.name
            description = group_.description
            if cn is not None:
                # If the description is None, who cares?
                res.append({'cn': cn, 'description': description})

    return jsonify(res)
