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
            form.current_password.errors.append("The old password or username is not correct")
        except python_freeipa.exceptions.PWChangePolicyError as e:
            form.password.errors.append(e.policy_error)
        except python_freeipa.exceptions.FreeIPAError as e:
            form.errors['non_field_errors'] = [e.message]

        if res and res.ok:
            flash(
                'Your password has been changed, '
                'please try to log in with the new one now.',
                'green',
            )
            return redirect(url_for('root'))
    return render_template('password-reset.html', password_reset_form=form)
