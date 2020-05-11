from flask import flash, redirect, session, url_for, render_template
from flask_babel import _
import python_freeipa

from noggin import app
from noggin.security.ipa import maybe_ipa_login
from noggin.utility import FormError, handle_form_errors
from noggin.form.sync_token import SyncTokenForm
from noggin.security.ipa import untouched_ipa_client


def handle_login_form(form):
    username = form.username.data.lower()
    password = form.password.data

    try:
        # This call will set the cookie itself, we don't have to.
        ipa = maybe_ipa_login(app, session, username, password)
    except python_freeipa.exceptions.PasswordExpired:
        flash(_('Password expired. Please reset it.'), 'danger')
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
        raise FormError("non_field_errors", _('Could not log in to the IPA server.'))

    if not ipa:
        app.logger.error(
            f'An unhandled situation happened while logging in user {username}: '
            f'could not connect to the IPA server'
        )
        raise FormError("non_field_errors", _('Could not log in to the IPA server.'))

    flash(_('Welcome, %(username)s!', username=username), 'success')
    return redirect(url_for('user', username=username))


@app.route('/otp/sync/', methods=['GET', 'POST'])
def otp_sync():
    form = SyncTokenForm()
    if form.validate_on_submit():
        with handle_form_errors(form):
            try:
                ipa = untouched_ipa_client(app)
                ipa.otptoken_sync(
                    user=form.username.data,
                    password=form.password.data,
                    first_code=form.first_code.data,
                    second_code=form.second_code.data,
                    token=form.token.data,
                )

                flash(_('Token successfully synchronized'), category='success')
                return redirect(url_for('root'))

            except python_freeipa.exceptions.BadRequest as e:
                app.logger.error(
                    f'An error {e.__class__.__name__} happened while syncing a token for user '
                    f'{form.username}: {e}'
                )
                raise FormError("non_field_errors", e.message)

    return render_template('sync-token.html', sync_form=form)
