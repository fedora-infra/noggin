import datetime
import random
import string

import jwt
import python_freeipa
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import _
from flask_mail import Message

from noggin.app import ipa_admin, mailer
from noggin.form.password_reset import (
    ForgottenPasswordForm,
    NewPasswordForm,
    PasswordResetForm,
)
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_session, untouched_ipa_client
from noggin.utility import messaging
from noggin.utility.controllers import require_self, user_or_404, with_ipa
from noggin.utility.forms import FormError, handle_form_errors
from noggin.utility.password_reset import PasswordResetLock
from noggin.utility.token import Audience, make_password_change_token, read_token
from noggin_messages import UserUpdateV1

from . import blueprint as bp


def _validate_change_pw_form(form, username, ipa=None):
    if ipa is None:
        ipa = untouched_ipa_client(current_app)

    current_password = form.current_password.data
    password = form.password.data
    otp = form.otp.data

    res = None
    try:
        res = ipa.change_password(username, password, current_password, otp)
    except python_freeipa.exceptions.PWChangeInvalidPassword:
        form.current_password.errors.append(
            _("The old password or username is not correct")
        )
    except python_freeipa.exceptions.PWChangePolicyError as e:
        form.password.errors.append(e.policy_error)
    except python_freeipa.exceptions.FreeIPAError as e:
        # If we made it here, we hit something weird not caught above. We didn't
        # bomb out, but we don't have IPA creds, either.
        current_app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while reseting '
            f'the password for user {username}: {e.message}'
        )
        form.non_field_errors.errors.append(_('Could not change password.'))

    if res and res.ok:
        flash(_('Your password has been changed'), 'success')
        current_app.logger.info(f'Password for {username} was changed')
        messaging.publish(
            UserUpdateV1(
                {"msg": {"agent": username, "user": username, "fields": ["password"]}}
            )
        )
    return res


@bp.route('/password-reset', methods=['GET', 'POST'])
def password_reset():
    # If already logged in, redirect to the logged in reset form
    ipa = maybe_ipa_session(current_app, session)
    username = session.get('noggin_username')
    if ipa and username:
        return redirect(url_for('.user_settings_password', username=username))

    username = request.args.get('username')
    if not username:
        abort(404)
    form = PasswordResetForm()

    if form.validate_on_submit():
        res = _validate_change_pw_form(form, username)
        if res and res.ok:
            return redirect(url_for('.root'))

    return render_template(
        'password-reset.html', password_reset_form=form, username=username
    )


@bp.route('/user/<username>/settings/password', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_password(ipa, username):
    user = User(user_or_404(ipa, username))
    form = PasswordResetForm()

    # check if an OTP token exists. If so, the user is using OTP.
    using_otp = bool(ipa.otptoken_find(o_ipatokenowner=username)["result"])

    if not using_otp:
        form.current_password.description = ""

    if form.validate_on_submit():
        res = _validate_change_pw_form(form, username, ipa)
        if res and res.ok:
            return redirect(url_for('.root'))

    return render_template(
        'user-settings-password.html',
        user=user,
        password_reset_form=form,
        activetab="password",
        using_otp=using_otp,
    )


@bp.route('/forgot-password/ask', methods=['GET', 'POST'])
def forgot_password_ask():
    form = ForgottenPasswordForm()
    if form.validate_on_submit():
        username = form.username.data
        lock = PasswordResetLock(username)
        valid_until = lock.valid_until()
        now = datetime.datetime.now()
        with handle_form_errors(form):
            if valid_until is not None and now < valid_until:
                wait_min = int((valid_until - now).total_seconds() / 60)
                wait_sec = int((valid_until - now).total_seconds() % 60)
                raise FormError(
                    "non_field_errors",
                    _(
                        'You have already requested a password reset, you need to wait '
                        '%(wait_min)s minute(s) and %(wait_sec)s seconds before you can request '
                        'another.',
                        wait_min=wait_min,
                        wait_sec=wait_sec,
                    ),
                )
            try:
                user = User(ipa_admin.user_show(a_uid=username)['result'])
            except python_freeipa.exceptions.NotFound:
                raise FormError(
                    "username", _("User %(username)s does not exist", username=username)
                )
            token = make_password_change_token(user)
            # Send the email
            email_context = {"token": token, "username": username}
            email = Message(
                body=render_template("forgot-password-email.txt", **email_context),
                html=render_template("forgot-password-email.html", **email_context),
                recipients=[user.mail],
                subject="Password reset procedure",
            )
            try:
                mailer.send(email)
            except ConnectionRefusedError as e:
                current_app.logger.error(
                    f"Impossible to send a password reset email: {e}"
                )
                flash(_("We could not send you an email, please retry later"), "danger")
                return redirect(url_for('.root'))
            if current_app.config["DEBUG"]:  # pragma: no cover
                current_app.logger.debug(email)
            lock.store()
            current_app.logger.info(
                f'{username} forgot their password and requested a token'
            )
            flash(
                _(
                    'An email has been sent to your address with instructions on how to reset '
                    'your password'
                ),
                "success",
            )
            return redirect(url_for('.root'))
    return render_template('forgot-password-ask.html', form=form)


@bp.route('/forgot-password/change', methods=['GET', 'POST'])
def forgot_password_change():
    token = request.args.get('token')
    if not token:
        flash('No token provided, please request one.', 'warning')
        return redirect(url_for('.forgot_password_ask'))
    try:
        token_data = read_token(token, audience=Audience.password_reset)
    except jwt.exceptions.DecodeError:
        flash(_("The token is invalid, please request a new one."), "warning")
        return redirect(url_for('.forgot_password_ask'))
    username = token_data["sub"]
    lock = PasswordResetLock(username)
    valid_until = lock.valid_until()
    now = datetime.datetime.now()
    if valid_until is None or now > valid_until:
        lock.delete()
        flash(_("The token has expired, please request a new one."), "warning")
        return redirect(url_for('.forgot_password_ask'))
    user = User(ipa_admin.user_show(a_uid=username)['result'])
    lpc = user.last_password_change
    if lpc is not None:
        lpc = lpc.isoformat()
    if lpc != token_data["lpc"]:
        lock.delete()
        flash(
            _(
                "Your password has been changed since you requested this token, please request "
                "a new one."
            ),
            "warning",
        )
        return redirect(url_for('.forgot_password_ask'))

    form = NewPasswordForm()
    if form.validate_on_submit():
        password = form.password.data
        # Generate a random temporary number.
        temp_password = ''.join(
            random.choices(string.ascii_letters + string.digits, k=24)
        )
        try:
            # Force change password to the random password, so that the password is not actually
            # changed to the given one in case the next step fails (because the OTP is wrong for
            # example)
            ipa_admin.user_mod(username, userpassword=temp_password)
            # Change the password as the user, so it's not expired.
            ipa = untouched_ipa_client(current_app)
            ipa.change_password(
                username,
                new_password=password,
                old_password=temp_password,
                otp=form.otp.data,
            )
        except python_freeipa.exceptions.PWChangePolicyError as e:
            lock.delete()
            flash(
                _(
                    'Your password has been changed, but it does not comply with the policy '
                    '(%(policy_error)s) and has thus been set as expired. You will be asked to '
                    'change it after logging in.',
                    policy_error=e.policy_error,
                ),
                'warning',
            )
            current_app.logger.info(
                f"Password for {username} was changed to a non-compliant password after "
                f"completing the forgotten password process."
            )
            # Send them to the login page, they will have to change their password
            # after login.
            return redirect(url_for('.root'))
        except python_freeipa.exceptions.PWChangeInvalidPassword:
            # The provided OTP was wrong
            current_app.logger.info(
                f"Password for {username} was changed to a random string because "
                f"the OTP token they provided was wrong."
            )
            # Oh noes, the token is now invalid since the user's password was changed! Let's
            # re-generate a token so they can keep going.
            user = User(ipa_admin.user_show(a_uid=username)['result'])
            token = make_password_change_token(user)
            form.otp.errors.append(_("Incorrect value."))
        except python_freeipa.exceptions.FreeIPAError as e:
            # If we made it here, we hit something weird not caught above.
            current_app.logger.error(
                f'An unhandled error {e.__class__.__name__} happened while reseting '
                f'the password for user {username}: {e.message}'
            )
            form.non_field_errors.errors.append(
                _('Could not change password, please try again.')
            )
        else:
            lock.delete()
            flash(_('Your password has been changed.'), 'success')
            current_app.logger.info(
                f"Password for {username} was changed after completing the forgotten "
                f"password process."
            )
            messaging.publish(
                UserUpdateV1(
                    {
                        "msg": {
                            "agent": username,
                            "user": username,
                            "fields": ["password"],
                        }
                    }
                )
            )
            return redirect(url_for('.root'))
    return render_template(
        'forgot-password-change.html', username=username, form=form, token=token
    )
