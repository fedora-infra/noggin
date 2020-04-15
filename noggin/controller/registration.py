import datetime
import re

from flask import flash, redirect, url_for
from flask_babel import _
from noggin_messages import UserCreateV1
import python_freeipa

from noggin import app, ipa_admin
from noggin.utility.locales import guess_locale
from noggin.utility import messaging, FormError
from noggin.security.ipa import untouched_ipa_client


# Errors coming from FreeIPA are specified by a field name that is different from our form field
# name. This dict maps one to the other. See the `cli_name` in
# https://pagure.io/freeipa/blob/master/f/ipaclient/remote_plugins/2_164/user.py
IPA_TO_FORM_FIELDS = {
    "login": "username",
    "first": "firstname",
    "last": "lastname",
    "password": "password",
    "email": "mail",
}


def _handle_registration_validation_error(username, e):
    mo = re.match(r"^invalid '([^']+)': (.+)$", e.message)
    if mo:
        ipa_field_name = mo.group(1)
        if ipa_field_name in IPA_TO_FORM_FIELDS:
            raise FormError(IPA_TO_FORM_FIELDS[ipa_field_name], mo.group(2))
    # Raise a generic error if we can't do better
    app.logger.error(
        f'An unhandled invalid value happened while registering user '
        f'{username}: {e.message}'
    )
    raise FormError("non_field_errors", e.message)


def handle_register_form(form):
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
            mail=form.mail.data,
            login_shell='/bin/bash',
            fascreationtime=f"{now.isoformat()}Z",
            faslocale=guess_locale(),
            fastimezone=app.config["USER_DEFAULTS"]["user_timezone"],
        )
    except python_freeipa.exceptions.DuplicateEntry as e:
        # the username already exists
        raise FormError("username", e.message)
    except python_freeipa.exceptions.ValidationError as e:
        # for example: invalid username. We don't know which field to link it to
        _handle_registration_validation_error(username, e)
    except python_freeipa.exceptions.FreeIPAError as e:
        app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while registering user '
            f'{username}: {e.message}'
        )
        raise FormError(
            "non_field_errors",
            _('An error occurred while creating the account, please try again.'),
        )

    # User creation succeeded. Send message.
    messaging.publish(UserCreateV1({"msg": {"agent": username, "user": username}}))

    # Now we fake a password change, so that it's not immediately
    # expired. This also logs the user in right away.
    try:
        ipa = untouched_ipa_client(app)
        ipa.change_password(username, password, password)
    except python_freeipa.exceptions.PWChangePolicyError as e:
        # The user is created but the password does not match the policy. Alert the user
        # and ask them to change their password.
        flash(
            _(
                'Your account has been created, but the password you chose does not comply '
                'with the policy (%(policy_error)s) and has thus been set as expired. '
                'You will be asked to change it after logging in.',
                policy_error=e.policy_error,
            ),
            'warning',
        )
        # Send them to the login page, they will have to change their password
        # after login.
        return redirect(url_for('root'))
    except python_freeipa.exceptions.FreeIPAError as e:
        app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while changing initial '
            f'password for user {username}: {e.message}'
        )
        # At this point the user has been created, they can't register again. Send them to
        # the login page with an appropriate warning.
        flash(
            _(
                'Your account has been created, but an error occurred while setting your '
                'password (%(message)s). You may need to change it after logging in.',
                message=e.message,
            ),
            'warning',
        )
        return redirect(url_for('root'))

    flash(
        _('Congratulations, you now have an account! Go ahead and sign in to proceed.'),
        'success',
    )
    return redirect(url_for('root'))
