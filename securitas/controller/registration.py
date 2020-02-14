import datetime

from flask import flash, redirect, url_for, render_template
import python_freeipa

from securitas import app, ipa_admin
from securitas.form.register_user import RegisterUserForm
from securitas.utility.locales import guess_locale
from securitas.security.ipa import untouched_ipa_client


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterUserForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        now = datetime.datetime.utcnow().replace(microsecond=0)
        # First, create the user.
        try:
            ipa_admin.user_add(
                username,
                form.firstname.data,
                form.lastname.data,
                f'{form.firstname.data} {form.lastname.data}',  # TODO ???
                user_password=password,
                login_shell='/bin/bash',
                fascreationtime=f"{now.isoformat()}Z",
                faslocale=guess_locale(),
                fastimezone=app.config["USER_DEFAULTS"]["user_timezone"],
            )
        except python_freeipa.exceptions.DuplicateEntry as e:
            # the username already exists
            form.username.errors.append(e.message)
        except python_freeipa.exceptions.ValidationError as e:
            # for example: invalid username. We don't know which field to link it to
            if e.message.startswith("invalid 'login': "):
                form.username.errors.append(e.message[len("invalid 'login': ") :])
            else:
                app.logger.error(
                    f'An unhandled invalid value happened while registering user '
                    f'{username}: {e.message}'
                )
                form.errors['non_field_errors'] = [e.message]
        except python_freeipa.exceptions.FreeIPAError as e:
            app.logger.error(
                f'An unhandled error {e.__class__.__name__} happened while registering user '
                f'{username}: {e.message}'
            )
            form.errors['non_field_errors'] = [
                'An error occurred while creating the account, please try again.'
            ]

        else:
            # User creation succeeded. Now we fake a password change, so that it's not immediately
            # expired. This also logs the user in right away.
            try:
                ipa = untouched_ipa_client(app)
                ipa.change_password(username, password, password)
            except python_freeipa.exceptions.PWChangePolicyError as e:
                # The user is created but the password does not match the policy. Alert the user
                # and ask them to change their password.
                flash(
                    f'Your account has been created, but the password you chose does not comply '
                    f'with the policy ({e.policy_error}) and has thus been set as expired. '
                    f'You will be asked to change it after logging in.',
                    'warning',
                )
                # Send them to the login page, they will have to change their password
                # after login.
                return redirect(url_for('login'))
            except python_freeipa.exceptions.FreeIPAError as e:
                app.logger.error(
                    f'An unhandled error {e.__class__.__name__} happened while changing initial '
                    f'password for user {username}: {e.message}'
                )
                # At this point the user has been created, they can't register again. Send them to
                # the login page with an appropriate warning.
                flash(
                    f'Your account has been created, but an error occurred while setting your '
                    f'password ({e.message}). You may need to change it after logging in.',
                    'warning',
                )
                return redirect(url_for('login'))
            else:
                flash(
                    'Congratulations, you now have an account! Go ahead and sign in to proceed.',
                    'success',
                )
                return redirect(url_for('root'))

    return render_template('register.html', register_form=form)
