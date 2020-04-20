import datetime
import re

from flask import flash, redirect, url_for, abort, render_template, request, session
from flask_babel import _
from flask_mail import Message
import jwt
from noggin_messages import UserCreateV1
import python_freeipa

from noggin import app, ipa_admin, mailer
from noggin.form.register_user import ResendValidationEmailForm, PasswordSetForm
from noggin.representation.user import User
from noggin.utility.locales import guess_locale
from noggin.utility.token import EmailValidationToken
from noggin.utility import messaging, FormError, handle_form_errors
from noggin.security.ipa import untouched_ipa_client, maybe_ipa_login


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


def _send_validation_email(user):
    token = EmailValidationToken.from_user(user).as_string()
    email_context = {"token": token, "user": user}
    email = Message(
        body=render_template("email-validation.txt", **email_context),
        html=render_template("email-validation.html", **email_context),
        recipients=[user.mail],
        subject=_("Verify your email address"),
    )
    if app.config["DEBUG"]:  # pragma: no cover
        app.logger.debug(email)
    try:
        mailer.send(email)
    except ConnectionRefusedError as e:
        app.logger.error(f"Impossible to send an address validation email: {e}")
        flash(
            _("We could not send you the address validation email, please retry later"),
            "danger",
        )


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
    now = datetime.datetime.utcnow().replace(microsecond=0)

    # First, create the stage user.
    try:
        user = ipa_admin.stageuser_add(
            username,
            form.firstname.data,
            form.lastname.data,
            mail=form.mail.data,
            login_shell='/bin/bash',
            fascreationtime=f"{now.isoformat()}Z",
            faslocale=guess_locale(),
            fastimezone=app.config["USER_DEFAULTS"]["user_timezone"],
        )
        user = User(user)
    except python_freeipa.exceptions.DuplicateEntry:
        raise FormError(
            "username", _("This username is already taken, please choose another one.")
        )
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

    # Send the address validation email
    _send_validation_email(user)
    return redirect(f"{url_for('confirm_registration')}?username={username}")


@app.route('/register/confirm', methods=["GET", "POST"])
def confirm_registration():
    username = request.args.get('username')
    if not username:
        abort(400, "No username provided")
    try:
        user = User(ipa_admin.stageuser_show(username))
    except python_freeipa.exceptions.NotFound:
        flash(_("The registration seems to have failed, please try again."), "warning")
        return redirect(f"{url_for('root')}?tab=register")

    form = ResendValidationEmailForm()
    if form.validate_on_submit():
        _send_validation_email(user)
        flash(
            _(
                'The address validation email has be sent again. Make sure it did not land in '
                'your spam folder'
            ),
            'success',
        )
        return redirect(request.url)

    return render_template('registration-confirmation.html', user=user, form=form)


@app.route('/register/activate', methods=["GET", "POST"])
def activate_account():
    register_url = f"{url_for('root')}?tab=register"
    token_string = request.args.get('token')
    if not token_string:
        flash(
            _('No token provided, please check your email validation link.'), 'warning'
        )
        return redirect(register_url)
    try:
        token = EmailValidationToken.from_string(token_string)
    except jwt.exceptions.DecodeError:
        flash(_("The token is invalid, please register again."), "warning")
        return redirect(register_url)
    if not token.is_valid():
        flash(_("This token is no longer valid, please register again."), "warning")
        return redirect(register_url)
    try:
        user = User(ipa_admin.stageuser_show(token.username))
    except python_freeipa.exceptions.NotFound:
        flash(_("This user cannot be found, please register again."), "warning")
        return redirect(register_url)
    if not user.mail == token.mail:
        app.logger.error(
            f'User {user.username} tried to validate a token for address {token.mail} while they '
            f'are registered with address {user.mail}, something fishy may be going on.'
        )
        flash(
            _(
                "The username and the email address don't match the token you used, "
                "please register again."
            ),
            "warning",
        )
        return redirect(register_url)

    form = PasswordSetForm()

    if form.validate_on_submit():
        with handle_form_errors(form):
            password = form.password.data
            # First we activate the stage user
            try:
                ipa_admin.stageuser_activate(user.username)
            except python_freeipa.exceptions.FreeIPAError as e:
                app.logger.error(
                    f'An unhandled error {e.__class__.__name__} happened while activating '
                    f'stage user {user.username}: {e.message}'
                )
                raise FormError(
                    "non_field_errors",
                    _(
                        "Something went wrong while activating your account, "
                        "please try again later."
                    ),
                )
            # User activation succeeded. Send message.
            messaging.publish(
                UserCreateV1({"msg": {"agent": user.username, "user": user.username}})
            )
            # Now we set the password.
            try:
                # First, set it as an admin. This will mark it as expired.
                ipa_admin.user_mod(user.username, userpassword=password)
                # And now we set it again as the user, so it is not expired any more.
                ipa = untouched_ipa_client(app)
                ipa.change_password(
                    user.username, new_password=password, old_password=password
                )
            except python_freeipa.exceptions.PWChangePolicyError as e:
                # The user is active but the password does not match the policy.
                # Tell the user what's going to happen.
                flash(
                    _(
                        'Your account has been activated, but the password you chose does not '
                        'comply with the policy (%(policy_error)s) and has thus been set as '
                        'expired. You will be asked to change it after logging in.',
                        policy_error=e.policy_error,
                    ),
                    'warning',
                )
                return redirect(url_for("root"))
            except python_freeipa.exceptions.ValidationError as e:
                # for example: invalid username. We don't know which field to link it to
                _handle_registration_validation_error(user.username, e)
            except python_freeipa.exceptions.FreeIPAError as e:
                app.logger.error(
                    f'An unhandled error {e.__class__.__name__} happened while changing initial '
                    f'password for user {user.username}: {e.message}'
                )
                # At this point the user has been activated, they can't register again. Send them to
                # the login page with an appropriate warning.
                flash(
                    _(
                        'Your account has been activated, but an error occurred while setting your '
                        'password (%(message)s). You may need to change it after logging in.',
                        message=e.message,
                    ),
                    'warning',
                )
                return redirect(url_for("root"))

            # Try to log them in directly, so they don't have to type their password again.
            try:
                ipa = maybe_ipa_login(app, session, user.username, password)
            except python_freeipa.exceptions.FreeIPAError:
                ipa = None
            if ipa:
                flash(
                    _(
                        'Congratulations, your account is now active! Welcome, %(name)s.',
                        name=user.name,
                    ),
                    'success',
                )
            else:
                # No shortcut for you, you'll have to login properly (maybe the password is
                # expired).
                flash(
                    _(
                        'Congratulations, your account is now active! Go ahead and sign in '
                        'to proceed.'
                    ),
                    'success',
                )
            return redirect(url_for('root'))

    return render_template('registration-activation.html', user=user, form=form)
