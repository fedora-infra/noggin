import os
from base64 import b32encode

import python_freeipa
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_babel import _
from pyotp import TOTP
from werkzeug.datastructures import MultiDict

from noggin.form.edit_user import (
    UserSettingsAddOTPForm,
    UserSettingsConfirmOTPForm,
    UserSettingsOTPNameChange,
    UserSettingsOTPStatusChange,
)
from noggin.representation.otptoken import OTPToken
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_login
from noggin.utility.controllers import require_self, user_or_404, with_ipa

from . import blueprint as bp

# Must be the same as KEY_LENGTH in ipaserver/plugins/otptoken.py
# For maximum compatibility, must be a multiple of 5.
OTP_KEY_LENGTH = 35


@bp.route('/user/<username>/settings/otp/', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_otp(ipa, username):
    addotpform = UserSettingsAddOTPForm(prefix="add-")
    confirmotpform = UserSettingsConfirmOTPForm(prefix="confirm-")
    user = User(user_or_404(ipa, username))
    secret = None

    if addotpform.validate_on_submit():
        description = addotpform.description.data
        password = addotpform.password.data
        if addotpform.otp.data:
            password += addotpform.otp.data

        try:
            maybe_ipa_login(current_app, session, username, password)
        except python_freeipa.exceptions.InvalidSessionPassword:
            addotpform.password.errors.append(_("Incorrect password"))
        else:
            secret = b32encode(os.urandom(OTP_KEY_LENGTH)).decode('ascii')
            # Prefill the form for the next step
            confirmotpform.process(
                MultiDict(
                    {"confirm-secret": secret, "confirm-description": description}
                )
            )
    if confirmotpform.validate_on_submit():
        try:
            ipa.otptoken_add(
                o_ipatokenowner=username,
                o_description=confirmotpform.description.data,
                o_ipatokenotpkey=confirmotpform.secret.data,
            )
        except python_freeipa.exceptions.FreeIPAError as e:
            current_app.logger.error(
                f'An error happened while creating an OTP token for user {username}: {e.message}'
            )
            confirmotpform.non_field_errors.errors.append(_('Cannot create the token.'))
        else:
            flash(_('The token has been created.'), "success")
            return redirect(url_for('.user_settings_otp', username=username))

    if confirmotpform.is_submitted():
        # This form is inside the modal. Keep a value in otp_uri or the modal will not open
        # to show the errors.
        secret = confirmotpform.secret.data

    # Compute the token URI
    if secret:
        description = addotpform.description.data or confirmotpform.description.data
        token = TOTP(secret)
        otp_uri = token.provisioning_uri(name=description, issuer_name=user.krbname)
    else:
        otp_uri = None

    # List existing tokens
    tokens = [
        OTPToken(t) for t in ipa.otptoken_find(o_ipatokenowner=username)["result"]
    ]
    tokens.sort(key=lambda t: t.description or "")

    return render_template(
        'user-settings-otp.html',
        addotpform=addotpform,
        confirmotpform=confirmotpform,
        user=user,
        activetab="otp",
        tokens=tokens,
        otp_uri=otp_uri,
    )


@bp.route('/user/<username>/settings/otp/rename/', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_rename(ipa, username):
    form = UserSettingsOTPNameChange()

    if form.validate_on_submit():
        try:
            ipa.otptoken_mod(
                a_ipatokenuniqueid=form.token.data,
                o_description=form.description.data,
            )
        except (
            python_freeipa.exceptions.BadRequest,
            python_freeipa.exceptions.FreeIPAError,
        ) as e:
            if e.message != "no modifications to be performed":
                flash(_('Cannot rename the token.'), 'danger')
                current_app.logger.error(
                    f'Something went wrong renaming an OTP token for user {username}: {e}'
                )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')

    return redirect(url_for('.user_settings_otp', username=username))


@bp.route('/user/<username>/settings/otp/disable/', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_disable(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        token = form.token.data
        try:
            ipa.otptoken_mod(a_ipatokenuniqueid=token, o_ipatokendisabled=True)
        except python_freeipa.exceptions.BadRequest as e:
            if (
                e.message
                == "Server is unwilling to perform: Can't disable last active token"
            ):
                flash(_('Sorry, You cannot disable your last active token.'), 'warning')
            else:
                flash(_('Cannot disable the token.'), 'danger')
                current_app.logger.error(
                    f'Something went wrong disabling an OTP token for user {username}: {e}'
                )
        except python_freeipa.exceptions.FreeIPAError as e:
            flash(_('Cannot disable the token.'), 'danger')
            current_app.logger.error(
                f'Something went wrong disabling an OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.user_settings_otp', username=username))


@bp.route('/user/<username>/settings/otp/enable/', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_enable(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        token = form.token.data
        try:
            ipa.otptoken_mod(a_ipatokenuniqueid=token, o_ipatokendisabled=False)
        except (
            python_freeipa.exceptions.BadRequest,
            python_freeipa.exceptions.FreeIPAError,
        ) as e:
            flash(
                _('Cannot enable the token. %(errormessage)s', errormessage=e), 'danger'
            )
            current_app.logger.error(
                f'Something went wrong enabling an OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.user_settings_otp', username=username))


@bp.route('/user/<username>/settings/otp/delete/', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_delete(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        token = form.token.data
        try:
            ipa.otptoken_del(a_ipatokenuniqueid=token)
        except python_freeipa.exceptions.BadRequest as e:
            if (
                e.message
                == "Server is unwilling to perform: Can't delete last active token"
            ):
                flash(_('Sorry, You cannot delete your last active token.'), 'warning')
            else:
                flash(_('Cannot delete the token.'), 'danger')
                current_app.logger.error(
                    f'Something went wrong deleting OTP token for user {username}: {e}'
                )
        except python_freeipa.exceptions.FreeIPAError as e:
            flash(_('Cannot delete the token.'), 'danger')
            current_app.logger.error(
                f'Something went wrong deleting OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.user_settings_otp', username=username))
