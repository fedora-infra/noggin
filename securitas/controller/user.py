from flask import flash, redirect, render_template, session, url_for

from securitas import app
from securitas.representation.group import Group
from securitas.representation.user import User
from securitas.utility import with_ipa, user_or_404

@app.route('/user/<username>/')
@with_ipa(app, session)
def user(ipa, username):
    user = User(user_or_404(ipa, username))
    groups = [Group(ipa.group_show(g)) for g in sorted(user.groups)]
    return render_template('user.html', user=user, groups=groups)

@app.route('/user/<username>/edit/')
@with_ipa(app, session)
def user_edit(ipa, username):
    # TODO: Maybe make this a decorator some day?
    if session.get('securitas_username') != username:
        flash(
            'You do not have permission to edit this account.',
            'red')
        return redirect(url_for('user', username=username))
    user = User(user_or_404(ipa, username))
    return render_template('user-edit.html', user=user)
