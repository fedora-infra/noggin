import os
from base64 import b32encode

import python_freeipa
from flask import (
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_babel import _
from markupsafe import Markup
from pyotp import TOTP
from werkzeug.datastructures import MultiDict

from noggin.app import ipa_admin
from noggin.form.edit_user import (
    AdminOTPResetForm,
    UserSettingsAddOTPForm,
    UserSettingsConfirmOTPForm,
    UserSettingsGenerateRecoveryForm,
    UserSettingsOTPNameChange,
    UserSettingsOTPStatusChange,
    UserSettingsRegenerateRecoveryForm,
)
from noggin.representation.otptoken import OTPToken
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_login
from noggin.utility import messaging
from noggin.utility.controllers import require_otp_admin, require_self, user_or_404, with_ipa
from noggin.utility.recovery_codes import generate_recovery_codes
from noggin_messages import UserUpdateV1

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
    generate_recovery_form = UserSettingsGenerateRecoveryForm(prefix="gen-")
    regenerate_recovery_form = UserSettingsRegenerateRecoveryForm(prefix="regen-")
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
            # Check if the user should generate recovery codes
            try:
                all_user_tokens = ipa.otptoken_find(
                    o_ipatokenowner=username
                )["result"]
            except python_freeipa.exceptions.FreeIPAError:
                current_app.logger.warning(
                    'Failed to check recovery tokens for user %s '
                    'after OTP creation',
                    username,
                )
                return redirect(
                    url_for('.user_settings_otp', username=username)
                )
            desc = current_app.config['OTP_RECOVERY_DESCRIPTION']
            has_recovery = any(
                OTPToken(t).is_recovery(desc) for t in all_user_tokens
            )
            if not has_recovery:
                if current_app.config.get('OTP_REQUIRE_RECOVERY_CODES'):
                    try:
                        codes, _token_id = _create_recovery_token(ipa, username)
                        return _render_otp_page(
                            ipa, username, recovery_codes=codes
                        )
                    except python_freeipa.exceptions.FreeIPAError as e:
                        current_app.logger.error(
                            f'Error auto-creating recovery codes for '
                            f'user {username}: {e.message}'
                        )
                flash(
                    Markup(
                        _(
                            '<a href="%(url)s">Generate recovery codes</a> '
                            'now to avoid being locked out.',
                            url=url_for(
                                '.user_settings_otp', username=username
                            )
                            + '#recovery-codes',
                        )
                    ),
                    "warning",
                )
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

    # List existing tokens, separating recovery tokens from regular ones
    try:
        all_tokens = [
            OTPToken(t)
            for t in ipa.otptoken_find(o_ipatokenowner=username)["result"]
        ]
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.error(
            'Failed to list OTP tokens for user %s', username
        )
        flash(_('Could not load OTP tokens.'), 'danger')
        return redirect(url_for('.user', username=username))
    tokens, recovery_token = _categorize_tokens(all_tokens)
    recovery_codes_remaining = _get_recovery_codes_remaining(ipa, recovery_token)

    return render_template(
        'user-settings-otp.html',
        addotpform=addotpform,
        confirmotpform=confirmotpform,
        generate_recovery_form=generate_recovery_form,
        regenerate_recovery_form=regenerate_recovery_form,
        user=user,
        activetab="otp",
        tokens=tokens,
        recovery_token=recovery_token,
        recovery_codes_remaining=recovery_codes_remaining,
        otp_uri=otp_uri,
    )


def _create_recovery_token(ipa_client, username):
    secret = b32encode(os.urandom(OTP_KEY_LENGTH)).decode('ascii')
    result = ipa_client.otptoken_add(
        o_ipatokenowner=username,
        o_type='hotp',
        o_ipatokenotpkey=secret,
        o_ipatokenotpdigits=8,
        o_ipatokenotpalgorithm='sha256',
        o_description=current_app.config['OTP_RECOVERY_DESCRIPTION'],
    )
    try:
        token_id = result['result']['ipatokenuniqueid'][0]
    except (KeyError, IndexError) as e:
        raise python_freeipa.exceptions.FreeIPAError(
            message=f'Unexpected response when creating recovery token: {e}',
            code=500,
        ) from e
    codes = generate_recovery_codes(
        secret, current_app.config['OTP_RECOVERY_CODE_COUNT']
    )
    return codes, token_id


def _get_recovery_codes_remaining(ipa, recovery_token):
    if not recovery_token:
        return None
    try:
        detail = OTPToken(
            ipa.otptoken_show(
                a_ipatokenuniqueid=recovery_token.uniqueid, o_all=True
            )["result"]
        )
        return max(
            0,
            current_app.config['OTP_RECOVERY_CODE_COUNT'] - detail.counter,
        )
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.warning(
            'Failed to fetch recovery token details for %s',
            recovery_token.uniqueid,
        )
        return None


def _categorize_tokens(all_tokens):
    desc = current_app.config['OTP_RECOVERY_DESCRIPTION']
    tokens = [t for t in all_tokens if not t.is_recovery(desc)]
    tokens.sort(key=lambda t: t.description or "")
    recovery_token = next(
        (t for t in all_tokens if t.is_recovery(desc)), None
    )
    return tokens, recovery_token


def _reauthenticate(form, auth_username):
    password = form.password.data
    if form.otp.data:
        password += form.otp.data
    try:
        maybe_ipa_login(current_app, session, auth_username, password)
        return True
    except python_freeipa.exceptions.InvalidSessionPassword:
        flash(_('Incorrect password'), 'danger')
        return False


def _render_otp_page(ipa, username, recovery_codes=None, user=None):
    if user is None:
        user = User(user_or_404(ipa, username))
    try:
        all_tokens = [
            OTPToken(t)
            for t in ipa.otptoken_find(o_ipatokenowner=username)["result"]
        ]
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.error(
            'Failed to list OTP tokens for user %s', username
        )
        if recovery_codes:
            all_tokens = []
            flash(
                _('Could not load your token list, but your new recovery '
                  'codes are shown below. Please save them now.'),
                'warning',
            )
        else:
            flash(_('Could not load OTP tokens.'), 'danger')
            return redirect(url_for('.user', username=username))
    tokens, recovery_token = _categorize_tokens(all_tokens)
    recovery_codes_remaining = _get_recovery_codes_remaining(ipa, recovery_token)

    response = make_response(
        render_template(
            'user-settings-otp.html',
            addotpform=UserSettingsAddOTPForm(prefix="add-"),
            confirmotpform=UserSettingsConfirmOTPForm(prefix="confirm-"),
            generate_recovery_form=UserSettingsGenerateRecoveryForm(prefix="gen-"),
            regenerate_recovery_form=UserSettingsRegenerateRecoveryForm(
                prefix="regen-"
            ),
            user=user,
            activetab="otp",
            tokens=tokens,
            recovery_token=recovery_token,
            recovery_codes_remaining=recovery_codes_remaining,
            otp_uri=None,
            recovery_codes=recovery_codes,
        )
    )
    if recovery_codes:
        response.headers['Cache-Control'] = 'no-store'
    return response


@bp.route('/user/<username>/settings/otp/rename/', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_rename(ipa, username):
    form = UserSettingsOTPNameChange()

    if form.validate_on_submit():
        token_id = form.token.data
        recovery_desc = current_app.config.get('OTP_RECOVERY_DESCRIPTION')
        if recovery_desc and form.description.data == recovery_desc:
            flash(
                _('This description is reserved for recovery codes.'),
                'warning',
            )
            return redirect(url_for('.user_settings_otp', username=username))

        try:
            ipa.otptoken_mod(
                a_ipatokenuniqueid=token_id,
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


@bp.route('/user/<username>/settings/otp/recovery/generate', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_recovery_generate(ipa, username):
    form = UserSettingsGenerateRecoveryForm(prefix="gen-")

    if form.validate_on_submit():
        if not _reauthenticate(form, username):
            return redirect(url_for('.user_settings_otp', username=username))

        # Check for existing recovery token
        try:
            existing = ipa.otptoken_find(
                o_ipatokenowner=username,
                o_type='hotp',
                o_description=current_app.config['OTP_RECOVERY_DESCRIPTION'],
            )
        except python_freeipa.exceptions.FreeIPAError:
            current_app.logger.error(
                'Failed to check existing recovery tokens for user %s',
                username,
            )
            flash(_('Cannot create recovery codes.'), 'danger')
            return redirect(url_for('.user_settings_otp', username=username))
        if existing['count'] > 0:
            flash(
                _('You already have recovery codes. Regenerate them instead.'),
                'warning',
            )
            return redirect(url_for('.user_settings_otp', username=username))

        try:
            codes, _token_id = _create_recovery_token(ipa, username)
        except python_freeipa.exceptions.FreeIPAError as e:
            current_app.logger.error(
                f'Error creating recovery token for user {username}: {e.message}'
            )
            flash(_('Cannot create recovery codes.'), 'danger')
            return redirect(url_for('.user_settings_otp', username=username))

        return _render_otp_page(ipa, username, recovery_codes=codes)

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.user_settings_otp', username=username))


@bp.route('/user/<username>/settings/otp/recovery/regenerate', methods=['POST'])
@with_ipa()
@require_self
def user_settings_otp_recovery_regenerate(ipa, username):
    form = UserSettingsRegenerateRecoveryForm(prefix="regen-")

    if form.validate_on_submit():
        if not _reauthenticate(form, username):
            return redirect(url_for('.user_settings_otp', username=username))

        # Find and delete existing recovery tokens
        try:
            existing = ipa.otptoken_find(
                o_ipatokenowner=username,
                o_type='hotp',
                o_description=current_app.config['OTP_RECOVERY_DESCRIPTION'],
            )
        except python_freeipa.exceptions.FreeIPAError:
            current_app.logger.error(
                'Failed to find recovery tokens for user %s', username
            )
            flash(_('Cannot regenerate recovery codes.'), 'danger')
            return redirect(url_for('.user_settings_otp', username=username))
        for t in existing['result']:
            try:
                ipa.otptoken_del(
                    a_ipatokenuniqueid=t['ipatokenuniqueid'][0],
                )
            except python_freeipa.exceptions.BadRequest as e:
                if "Can't delete last active token" in str(e):
                    flash(
                        _(
                            'Cannot regenerate recovery codes while they are '
                            'your only active token. Add a regular OTP token '
                            'first.'
                        ),
                        'warning',
                    )
                else:
                    current_app.logger.error(
                        'Error deleting recovery token for user %s: %s',
                        username,
                        e,
                    )
                    flash(_('Cannot regenerate recovery codes.'), 'danger')
                return redirect(
                    url_for('.user_settings_otp', username=username)
                )
            except python_freeipa.exceptions.FreeIPAError as e:
                current_app.logger.error(
                    f'Error deleting old recovery token for user {username}: {e.message}'
                )
                flash(_('Cannot regenerate recovery codes.'), 'danger')
                return redirect(url_for('.user_settings_otp', username=username))

        try:
            codes, _token_id = _create_recovery_token(ipa, username)
        except python_freeipa.exceptions.FreeIPAError as e:
            current_app.logger.error(
                f'Error creating recovery token for user {username}: {e.message}'
            )
            flash(_('Cannot create recovery codes.'), 'danger')
            return redirect(url_for('.user_settings_otp', username=username))

        return _render_otp_page(ipa, username, recovery_codes=codes)

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.user_settings_otp', username=username))


@bp.route('/user/<username>/settings/otp/admin-reset', methods=['GET', 'POST'])
@with_ipa()
@require_otp_admin
def user_settings_otp_admin_reset(ipa, username):
    user = User(user_or_404(ipa, username))
    form = AdminOTPResetForm(prefix="admin-reset-")

    if form.validate_on_submit():
        admin_username = session.get('noggin_username')
        if not _reauthenticate(form, admin_username):
            return redirect(
                url_for('.user_settings_otp_admin_reset', username=username)
            )

        try:
            codes, new_token_id = _create_recovery_token(ipa_admin, username)
        except python_freeipa.exceptions.FreeIPAError as e:
            current_app.logger.error(
                f'Admin {admin_username} failed to create recovery token '
                f'for user {username}: {e}'
            )
            flash(_('Error creating recovery codes.'), 'danger')
            return redirect(
                url_for('.user_settings_otp_admin_reset', username=username)
            )

        try:
            all_tokens = ipa_admin.otptoken_find(o_ipatokenowner=username)
        except python_freeipa.exceptions.FreeIPAError as e:
            current_app.logger.error(
                'Failed to list tokens for user %s after recovery '
                'token creation: %s',
                username,
                e,
            )
            flash(
                _(
                    'Recovery codes were created but old tokens could '
                    'not be removed. Please try again.'
                ),
                'warning',
            )
            return redirect(
                url_for('.user_settings_otp_admin_reset', username=username)
            )

        for t in all_tokens['result']:
            token_id = t['ipatokenuniqueid'][0]
            if token_id == new_token_id:
                continue
            try:
                ipa_admin.otptoken_del(
                    a_ipatokenuniqueid=token_id,
                )
            except python_freeipa.exceptions.FreeIPAError as e:
                current_app.logger.error(
                    f'Admin {admin_username} failed to delete token '
                    f'{token_id} for user {username}: {e}'
                )
                flash(_('Error deleting OTP tokens.'), 'danger')
                return redirect(
                    url_for('.user_settings_otp_admin_reset', username=username)
                )

        current_app.logger.info(
            f'Admin {admin_username} reset OTP for user {username}'
        )
        messaging.publish(
            UserUpdateV1(
                {
                    "msg": {
                        "agent": admin_username,
                        "user": username,
                        "fields": ["otp_reset"],
                    }
                }
            )
        )
        flash(
            _('OTP tokens have been reset for %(username)s.', username=username),
            'success',
        )
        response = make_response(
            render_template(
                'user-settings-otp-admin-reset.html',
                target_user=user,
                recovery_codes=codes,
                form=form,
            )
        )
        response.headers['Cache-Control'] = 'no-store'
        return response

    try:
        all_tokens = [
            OTPToken(t)
            for t in ipa_admin.otptoken_find(
                o_ipatokenowner=username
            )["result"]
        ]
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.error(
            'Failed to list OTP tokens for user %s', username
        )
        flash(_('Could not load OTP tokens.'), 'danger')
        return redirect(url_for('.user', username=username))
    tokens, recovery_token = _categorize_tokens(all_tokens)

    return render_template(
        'user-settings-otp-admin-reset.html',
        target_user=user,
        tokens=tokens,
        recovery_token=recovery_token,
        form=form,
    )
