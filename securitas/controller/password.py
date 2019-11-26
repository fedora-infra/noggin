from flask import flash, render_template, redirect, request, url_for
import python_freeipa

from securitas import app
from securitas.security.ipa import untouched_ipa_client

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
