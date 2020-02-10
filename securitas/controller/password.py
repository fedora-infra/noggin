from flask import abort, flash, render_template, redirect, request, url_for, session
import python_freeipa

from securitas import app
from securitas.security.ipa import untouched_ipa_client, maybe_ipa_session
from securitas.utility import with_ipa
from securitas.form.password_reset import PasswordResetForm


def _validate_change_pw_form(form, username, ipa=None):
    if ipa is None:
        ipa = untouched_ipa_client(app)

    current_password = form.current_password.data
    password = form.password.data

    res = None
    try:
        res = ipa.change_password(username, password, current_password)
    except python_freeipa.exceptions.PWChangeInvalidPassword:
        form.current_password.errors.append(
            "The old password or username is not correct"
        )
    except python_freeipa.exceptions.PWChangePolicyError as e:
        form.password.errors.append(e.policy_error)
    except python_freeipa.exceptions.FreeIPAError as e:
        # If we made it here, we hit something weird not caught above. We didn't
        # bomb out, but we don't have IPA creds, either.
        app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while reseting '
            f'the password for user {username}: {e.message}'
        )
        form.errors['non_field_errors'] = ['Could not change password.']

    if res and res.ok:
        flash('Your password has been changed', 'success')
        app.logger.info(f'Password for {username} was changed')
    return res


@app.route('/password-reset', methods=['GET', 'POST'])
def password_reset():
    # If already logged in, redirect to the logged in reset form
    ipa = maybe_ipa_session(app, session)
    username = session.get('securitas_username')
    if ipa and username:
        return redirect(url_for('auth_password_reset', username=username))

    username = request.args.get('username')
    if not username:
        abort(404)
    form = PasswordResetForm()

    if form.validate_on_submit():
        res = _validate_change_pw_form(form, username)
        if res and res.ok:
            return redirect(url_for('root'))

    return render_template(
        'password-reset.html', password_reset_form=form, username=username
    )


@app.route('/user/<username>/password-reset', methods=['GET', 'POST'])
@with_ipa(app, session)
def auth_password_reset(ipa, username):
    if session.get('securitas_username') != username:
        flash('You do not have permission to edit this account.', 'danger')
        return redirect(url_for('root'))

    form = PasswordResetForm()

    if form.validate_on_submit():
        res = _validate_change_pw_form(form, username, ipa)
        if res and res.ok:
            return redirect(url_for('root'))

    return render_template('password-reset.html', password_reset_form=form)
