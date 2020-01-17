from flask import flash, redirect, session, url_for, render_template
import python_freeipa

from securitas import app
from securitas.form.login_user import LoginUserForm
from securitas.security.ipa import maybe_ipa_login, maybe_ipa_session


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


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginUserForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        try:
            # This call will set the cookie itself, we don't have to.
            ipa = maybe_ipa_login(app, session, username, password)
        except python_freeipa.exceptions.PasswordExpired:
            flash('Password expired. Please reset it.', 'red')
            return redirect(url_for('password_reset'))
        except python_freeipa.exceptions.Unauthorized as e:
            form.errors['non_field_errors'] = [e.message]
        except python_freeipa.exceptions.FreeIPAError as e:
            # If we made it here, we hit something weird not caught above. We didn't
            # bomb out, but we don't have IPA creds, either. Boot us back to /.
            app.logger.error(
                f'An unhandled error {e.__class__.__name__} happened while logging in user '
                f'{username}: {e.message}'
            )
            form.errors['non_field_errors'] = ['Could not log in to the IPA server.']
        else:
            if ipa:
                flash(f'Welcome, {username}!', 'green')
                return redirect(url_for('user', username=username))
            else:
                app.logger.error(
                    f'An unhandled situation happened while logging in user {username}: '
                    f'could not connect to the IPA server'
                )
                form.errors['non_field_errors'] = [
                    'Could not log in to the IPA server.'
                ]
    return render_template('login.html', login_form=form)
