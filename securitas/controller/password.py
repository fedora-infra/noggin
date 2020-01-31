from flask import flash, render_template, redirect, url_for
import python_freeipa

from securitas import app
from securitas.security.ipa import untouched_ipa_client
from securitas.form.password_reset import PasswordResetForm


@app.route('/password-reset', methods=['GET', 'POST'])
def password_reset():
    form = PasswordResetForm()

    if form.validate_on_submit():
        username = form.username.data
        current_password = form.current_password.data
        password = form.password.data

        ipa = untouched_ipa_client(app)
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
                f'An unhandled error {e.__class__.__name__} happened while reseting the password for user '
                f'{username}: {e.message}'
            )
            form.errors['non_field_errors'] = ['Could not change password.']

        if res and res.ok:
            flash(
                'Your password has been changed, '
                'please try to log in with the new one now.',
                'green',
            )
            return redirect(url_for('root'))
    return render_template('password-reset.html', password_reset_form=form)
