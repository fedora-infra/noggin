from flask import flash, redirect, request, url_for
import python_freeipa

from securitas import app, ipa_admin
from securitas.security.ipa import untouched_ipa_client

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
        ipa_admin.user_add(
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
