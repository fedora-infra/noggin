from flask import Flask, render_template, request, flash, redirect, url_for, make_response, session
from flask_wtf.csrf import CSRFProtect
import python_freeipa

from securitas.security.ipa import maybe_ipa_login, maybe_ipa_session, untouched_ipa_client
from securitas.security.ipa_admin import IPAAdmin
from securitas.utility import gravatar

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config.from_envvar('SECURITAS_CONFIG_PATH')
if app.config.get('TEMPLATES_AUTO_RELOAD'):
    app.jinja_env.auto_reload = True

ipa_admin = IPAAdmin(app)

@app.context_processor
def inject_global_template_vars():
    ipa = maybe_ipa_session(app, session)
    # TODO: move project out to config var
    return dict(
        project="The Fedora Project",
        gravatar=gravatar,
        ipa=ipa,
        current_user=ipa.user_find(whoami=True) if ipa else None
    )

@app.route('/')
def root():
    ipa = maybe_ipa_session(app, session)
    username = session.get('securitas_username_insecure')
    if ipa and username:
        return redirect(url_for('user', username=username))
    # Kick any non-authed user back to the login form.
    return render_template('index.html')

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

@app.route('/password-reset', methods=['GET', 'POST'])
def password_reset():
    if request.method == 'GET':
        return render_template('password-reset.html')

    username = request.form.get('username')
    current_password = request.form.get('current_password')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    if not all([username, current_password, password, password_confirm]):
        flash('Please fill in all fields to reset your password', 'red')
        return redirect(url_for('password_reset'))

    if password != password_confirm:
        flash('Password and confirmation did not match.', 'red')
        return redirect(url_for('password_reset'))

    ipa = untouched_ipa_client(app)
    res = None
    try:
        res = ipa.change_password(username, password, current_password)
    except python_freeipa.exceptions.PWChangePolicyError as e:
        flash(
            'Failed to reset your password (policy error): %s' % str(e.policy_error),
            'red')
        return redirect(url_for('password_reset'))
    except python_freeipa.exceptions.PWChangeInvalidPassword as e:
        flash(
            'Failed to reset your password (invalid current password).',
            'red')
        return redirect(url_for('password_reset'))
    except python_freeipa.exceptions.FreeIPAError as e:
        flash('Failed to reset your password: %s' % str(e), 'red')
        return redirect(url_for('password_reset'))

    if res and res.ok:
        flash('Your password has been changed, ' \
              'please try to log in with the new one now.',
              'green')
        return redirect(url_for('root'))

    # If we made it here, we hit something weird not caught above. We didn't
    # bomb out, but we don't have a valid/good response from IPA. Boot the user
    # back to /.
    flash('Something went wrong and your password might not have been ' \
          'changed. Please try again, or report the issue to the system ' \
          'administrator.',
          'red')
    return redirect(url_for('root'))

@app.route('/register', methods=['POST'])
def register():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    if not all([first_name, last_name, username, password, password_confirm]):
        flash('Please fill in all fields to register an account.', 'red')
        return redirect(url_for('root'))

    if password != password_confirm:
        flash('Password and confirmation did not match.', 'red')
        return redirect(url_for('root'))

    try:
        add = ipa_admin.user_add(
            username,
            first_name,
            last_name,
            '%s %s' % (first_name, last_name), # TODO ???
            user_password=password,
            login_shell='/bin/bash')

        # Now we fake a password change, so that it's not immediately expired.
        # This also logs the user in right away.
        ipa = untouched_ipa_client(app)
        ipa.change_password(username, password, password)
    except python_freeipa.exceptions.FreeIPAError as e:
        print(e)
        flash(
            'An error occurred while creating the account, please try again.',
            'red')
        return redirect(url_for('root'))

    flash(
        'Congratulations, you now have an account! Go ahead and sign in to ' \
        'proceed.',
        'green')

    return redirect(url_for('root'))

@app.route('/user/<username>/')
def user(username):
    ipa = maybe_ipa_session(app, session)
    if ipa:
        user = ipa.user_show(username)
        return render_template('user.html', user=user)
    else:
        flash('Please log in to continue.', 'orange')
        return redirect(url_for('root'))

@app.route('/group/<groupname>/')
def group(groupname):
    ipa = maybe_ipa_session(app, session)
    if ipa:
        group = ipa.group_show(groupname)
        return render_template('group.html', group=group)
    else:
        flash('Please log in to continue.', 'orange')
        return redirect(url_for('root'))
