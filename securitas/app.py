from flask import render_template, request, flash, redirect, url_for, make_response, session, jsonify
import python_freeipa

from securitas import app, ipa_admin
from securitas.controller.authentication import login, logout
from securitas.controller.group import group, groups
from securitas.controller.password import password_reset
from securitas.controller.registration import register
from securitas.controller.user import user
from securitas.security.ipa import maybe_ipa_login, maybe_ipa_session, untouched_ipa_client
from securitas.utility import Get, gravatar, with_ipa

@app.context_processor
def inject_global_template_vars():
    ipa = maybe_ipa_session(app, session)
    # TODO: move project out to config var
    return dict(
        project="The Fedora Project",
        gravatar=gravatar,
        Get=Get,
        ipa=ipa,
        current_user=ipa.user_find(whoami=True) if ipa else None
    )

@app.route('/')
def root():
    ipa = maybe_ipa_session(app, session)
    username = session.get('securitas_username')
    if ipa and username:
        return redirect(url_for('user', username=username))
    # Kick any non-authed user back to the login form.
    return render_template('index.html')

@app.route('/search/json')
@with_ipa(app, session)
def search_json(ipa):
    username = request.args.get('username')
    group = request.args.get('group')

    res = []

    if username:
        users = ipa.user_find(username)

        for user in users['result']:
            uid = Get(user)['uid'][0].final
            cn = Get(user)['cn'][0].final
            if uid is not None:
                # If the cn is None, who cares?
                res.append({ 'uid': uid, 'cn': cn })

    if group:
        groups = ipa.group_find(group)
        for group in groups['result']:
            cn = Get(group)['cn'][0].final
            description = Get(group)['description'][0].final
            if cn is not None:
                # If the description is None, who cares?
                res.append({ 'cn': cn, 'description': description })

    return jsonify(res)
