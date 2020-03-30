from flask import flash, redirect, session, url_for
import python_freeipa

from noggin import app
from noggin.security.ipa import maybe_ipa_login
from noggin.utility import FormError


def handle_login_form(form):
    username = form.username.data
    password = form.password.data

    try:
        # This call will set the cookie itself, we don't have to.
        ipa = maybe_ipa_login(app, session, username, password)
    except python_freeipa.exceptions.PasswordExpired:
        flash('Password expired. Please reset it.', 'danger')
        return redirect(url_for('password_reset', username=username))
    except python_freeipa.exceptions.Unauthorized as e:
        raise FormError("non_field_errors", e.message)
    except python_freeipa.exceptions.FreeIPAError as e:
        # If we made it here, we hit something weird not caught above. We didn't
        # bomb out, but we don't have IPA creds, either.
        app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while logging in user '
            f'{username}: {e.message}'
        )
        raise FormError("non_field_errors", "Could not log in to the IPA server.")

    if not ipa:
        app.logger.error(
            f'An unhandled situation happened while logging in user {username}: '
            f'could not connect to the IPA server'
        )
        raise FormError("non_field_errors", "Could not log in to the IPA server.")

    flash(f'Welcome, {username}!', 'success')
    return redirect(url_for('user', username=username))
