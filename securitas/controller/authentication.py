from flask import flash, render_template, redirect, request, session, url_for
import python_freeipa

from securitas import app
from securitas.security.ipa import maybe_ipa_login, maybe_ipa_session

@app.route('/logout')
def logout():
    ipa = maybe_ipa_session(app, session)
    if ipa:
        ipa.logout()
    session.clear()
    return redirect(url_for('root'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        flash('Please provide both a username and a password.', 'red')
        return redirect(url_for('root'))

    try:
        # This call will set the cookie itself, we don't have to.
        ipa = maybe_ipa_login(app, session, username, password)
    except python_freeipa.exceptions.PasswordExpired as e:
        flash('Password expired. Please reset it.', 'red')
        return redirect(url_for('password_reset'))
    except python_freeipa.exceptions.Unauthorized as e:
        flash(str(e), 'red')
        return redirect(url_for('root'))

    if ipa:
        flash('Welcome, %s!' % username, 'green')
        return redirect(url_for('user', username=username))

    # If we made it here, we hit something weird not caught above. We didn't
    # bomb out, but we don't have IPA creds, either. Boot us back to /.
    flash('Could not log in to the IPA server.', 'red')
    return redirect(url_for('root'))
