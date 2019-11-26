from flask import render_template, request, redirect, url_for, session, jsonify

from securitas import app
from securitas.controller.authentication import login, logout # noqa: F401
from securitas.controller.group import group, groups # noqa: F401
from securitas.controller.password import password_reset # noqa: F401
from securitas.controller.registration import register # noqa: F401
from securitas.controller.user import user # noqa: F401
from securitas.security.ipa import maybe_ipa_session # noqa: F401
from securitas.utility import Get, gravatar, with_ipa # noqa: F401

@app.context_processor
def inject_global_template_vars():
    ipa = maybe_ipa_session(app, session)
    # TODO: move project out to config var
    return dict(
        project="The Fedora Project",
        gravatar=gravatar,
        Get=Get,
        ipa=ipa,
        current_user=ipa.user_find(whoami=True) if ipa else None,
        current_username=session.get('securitas_username'),
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

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
    groupname = request.args.get('group')

    res = []

    if username:
        users_ = ipa.user_find(username)

        for user_ in users_['result']:
            uid = Get(user_)['uid'][0].final
            cn = Get(user_)['cn'][0].final
            if uid is not None:
                # If the cn is None, who cares?
                res.append({ 'uid': uid, 'cn': cn })

    if groupname:
        groups_ = ipa.group_find(groupname)
        for group_ in groups_['result']:
            cn = Get(group_)['cn'][0].final
            description = Get(group_)['description'][0].final
            if cn is not None:
                # If the description is None, who cares?
                res.append({ 'cn': cn, 'description': description })

    return jsonify(res)
