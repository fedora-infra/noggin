import time

import python_freeipa
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import _

from noggin.app import ipa_admin
from noggin.form.sync_token import SyncTokenForm
from noggin.security.ipa import NoIPAServer, maybe_ipa_login, untouched_ipa_client
from noggin.security.kerberos import (
    KerberosAuthError,
    KerberosConfigError,
    ipa_login_with_kerberos,
)
from noggin.utility.controllers import get_username_from_email
from noggin.utility.forms import FormError, handle_form_errors
from noggin.utility.passkey import (
    b64url_decode,
    b64url_encode,
    generate_challenge,
    parse_passkey_attr,
    verify_assertion,
)

from . import blueprint as bp


def handle_login_form(form):
    try:
        username = get_username_from_email(ipa_admin, form.username.data)
    except ValueError as e:
        raise FormError("username", str(e))

    password = form.password.data
    if form.otp.data:
        password += form.otp.data

    try:
        # This call will set the cookie itself, we don't have to.
        ipa = maybe_ipa_login(current_app, session, username, password)
    except python_freeipa.exceptions.PasswordExpired:
        flash(_('Password expired. Please reset it.'), 'danger')
        return redirect(url_for('.password_reset', username=username))
    except python_freeipa.exceptions.Unauthorized as e:
        raise FormError("non_field_errors", e.message)
    except python_freeipa.exceptions.FreeIPAError as e:
        # If we made it here, we hit something weird not caught above. We didn't
        # bomb out, but we don't have IPA creds, either.
        current_app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while logging in user '
            f'{username}: {e.message}'
        )
        raise FormError("non_field_errors", _('Could not log in to the IPA server.'))

    if not ipa:
        current_app.logger.error(
            f'An unhandled situation happened while logging in user {username}: '
            f'could not connect to the IPA server'
        )
        raise FormError("non_field_errors", _('Could not log in to the IPA server.'))

    flash(_('Welcome, %(username)s!', username=username), 'success')
    next = request.args.get("next")
    # Keep the same domain
    if next and not next.startswith("/"):
        next = None
    if next is None:
        next = url_for('.user', username=username)
    return redirect(next)


@bp.route('/otp/sync/', methods=['GET', 'POST'])
def otp_sync():
    form = SyncTokenForm()
    if form.validate_on_submit():
        with handle_form_errors(form):
            try:
                ipa = untouched_ipa_client(current_app, session)
                ipa.otptoken_sync(
                    user=form.username.data,
                    password=form.password.data,
                    first_code=form.first_code.data,
                    second_code=form.second_code.data,
                    token=form.token.data,
                )

                flash(_('Token successfully synchronized'), category='success')
                return redirect(url_for('.root'))

            except python_freeipa.exceptions.BadRequest as e:
                current_app.logger.error(
                    f'An error {e.__class__.__name__} happened while syncing a token for user '
                    f'{form.username}: {e}'
                )
                raise FormError("non_field_errors", e.message)
            except NoIPAServer:
                raise FormError("non_field_errors", _("No IPA server available"))

    return render_template('sync-token.html', sync_form=form)


@bp.route('/passkey/login-begin', methods=['POST'])
def passkey_login_begin():
    if not current_app.config.get('KERBEROS_KEYTAB'):
        return jsonify({'error': 'Passkey login is not available.'}), 400

    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({'error': 'Username is required.'}), 400

    username = data['username']

    try:
        username = get_username_from_email(ipa_admin, username)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        user_data = ipa_admin.user_show(a_uid=username, o_all=True)['result']
    except python_freeipa.exceptions.NotFound:
        return jsonify({'error': _('User not found.')}), 400
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.error(
            "IPA error looking up user %s for passkey login", username
        )
        return jsonify({'error': _('Could not look up user.')}), 500

    raw_passkeys = user_data.get('ipapasskey', [])
    passkeys = [pk for raw in raw_passkeys if (pk := parse_passkey_attr(raw))]

    if not passkeys:
        return jsonify({'error': _('No passkeys registered for this user.')}), 400

    rp_id = current_app.config.get('PASSKEY_RP_ID') or current_app.config[
        'FREEIPA_DOMAIN'
    ]

    challenge = generate_challenge()
    session['noggin_passkey_auth_challenge'] = b64url_encode(challenge)
    session['noggin_passkey_auth_username'] = username
    session['noggin_passkey_auth_time'] = time.time()

    allow_credentials = [
        {
            'type': 'public-key',
            'id': b64url_encode(pk.credential_id),
        }
        for pk in passkeys
    ]

    return jsonify(
        {
            'challenge': b64url_encode(challenge),
            'rpId': rp_id,
            'timeout': 300000,
            'allowCredentials': allow_credentials,
            'userVerification': 'preferred',
        }
    )


@bp.route('/passkey/login-complete', methods=['POST'])
def passkey_login_complete():
    if not current_app.config.get('KERBEROS_KEYTAB'):
        return jsonify({'error': 'Passkey login is not available.'}), 400

    stored_challenge_b64 = session.pop('noggin_passkey_auth_challenge', None)
    stored_username = session.pop('noggin_passkey_auth_username', None)
    challenge_time = session.pop('noggin_passkey_auth_time', None)

    if not stored_challenge_b64 or not stored_username:
        return jsonify({'error': _('Challenge missing or expired.')}), 400

    if challenge_time is not None and (time.time() - challenge_time) > 300:
        return jsonify({'error': _('Challenge expired. Please try again.')}), 400

    stored_challenge = b64url_decode(stored_challenge_b64)

    data = request.get_json()
    if not data:
        return jsonify({'error': _('Missing request body.')}), 400

    response = data.get('response', {})
    credential_id_b64 = data.get('id')
    if (
        not credential_id_b64
        or not response.get('clientDataJSON')
        or not response.get('authenticatorData')
        or not response.get('signature')
    ):
        return jsonify({'error': _('Missing assertion data.')}), 400

    try:
        user_data = ipa_admin.user_show(
            a_uid=stored_username, o_all=True
        )['result']
    except python_freeipa.exceptions.FreeIPAError:
        current_app.logger.error(
            "IPA error looking up user %s during passkey login", stored_username
        )
        return jsonify({'error': _('Could not look up user.')}), 500

    raw_passkeys = user_data.get('ipapasskey', [])
    passkeys = [pk for raw in raw_passkeys if (pk := parse_passkey_attr(raw))]

    credential_id = b64url_decode(credential_id_b64)
    matched_passkey = None
    for pk in passkeys:
        if pk.credential_id == credential_id:
            matched_passkey = pk
            break

    if not matched_passkey:
        return jsonify({'error': _('Unknown credential.')}), 400

    rp_id = current_app.config.get('PASSKEY_RP_ID') or current_app.config[
        'FREEIPA_DOMAIN'
    ]

    try:
        verify_assertion(
            client_data_json_b64=response['clientDataJSON'],
            authenticator_data_b64=response['authenticatorData'],
            signature_b64=response['signature'],
            expected_challenge=stored_challenge,
            expected_rp_id=rp_id,
            expected_origin=request.host_url.rstrip('/'),
            public_key_der=matched_passkey.public_key_der,
            credential_id=credential_id,
        )
    except ValueError as e:
        current_app.logger.warning("Passkey assertion verification failed: %s", e)
        return jsonify({'error': _('Passkey verification failed.')}), 400

    try:
        ipa_login_with_kerberos(current_app, session, stored_username)
    except KerberosConfigError as e:
        current_app.logger.error("Kerberos config error: %s", e)
        return jsonify({'error': _('Passkey login is not available.')}), 500
    except KerberosAuthError as e:
        current_app.logger.error(
            "Kerberos auth failed for user %s: %s", stored_username, e
        )
        return jsonify({'error': _('Could not establish session.')}), 500

    flash(
        _('Welcome, %(username)s!', username=stored_username),
        'success',
    )

    next_url = request.args.get("next")
    if next_url and not next_url.startswith("/"):
        next_url = None
    if next_url is None:
        next_url = url_for('.user', username=stored_username)

    return jsonify({'ok': True, 'redirect': next_url})
