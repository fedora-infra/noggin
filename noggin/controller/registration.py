import datetime
import re

import jwt
import python_freeipa
from flask import (
    abort,
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
from flask_mail import Message
from translitcodec import codecs
from unidecode import unidecode

from noggin.app import csrf, ipa_admin, mailer
from noggin.form.register_user import (
    PasswordSetForm,
    RegisteringActionForm,
    ResendValidationEmailForm,
)
from noggin.l10n import guess_locale
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_login, untouched_ipa_client
from noggin.signals import stageuser_created, user_registered
from noggin.utility.controllers import with_ipa
from noggin.utility.forms import FormError, handle_form_errors
from noggin.utility.token import Audience, make_token, read_token

from . import blueprint as bp


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
    ttl = current_app.config["ACTIVATION_TOKEN_EXPIRATION"]
    token = make_token(
        {"sub": user.username, "mail": user.mail},
        audience=Audience.email_validation,
        ttl=ttl,
    )
    valid_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=ttl)
    email_context = {
        "token": token,
        "user": user,
        "ttl": ttl,
        "valid_until": valid_until,
    }
    email = Message(
        body=render_template("email-validation.txt", **email_context),
        html=render_template("email-validation.html", **email_context),
        recipients=[user.mail],
        subject=_("Verify your email address"),
    )
    if current_app.config["DEBUG"]:  # pragma: no cover
        current_app.logger.debug(email)
    try:
        mailer.send(email)
    except ConnectionRefusedError as e:
        current_app.logger.error(f"Impossible to send an address validation email: {e}")
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
    current_app.logger.error(
        f'An unhandled invalid value happened while registering user '
        f'{username}: {e.message}'
    )
    raise FormError("non_field_errors", e.message)


def handle_register_form(form):
    username = form.username.data
    now = datetime.datetime.utcnow().replace(microsecond=0)
    common_name = f"{form.firstname.data} {form.lastname.data}"
    gecos = (
        unidecode(codecs.encode(common_name, "translit/long"))
        .replace("  ", " ")
        .strip()
    )
    # First, create the stage user.
    try:
        user = ipa_admin.stageuser_add(
            username,
            o_givenname=form.firstname.data,
            o_sn=form.lastname.data,
            o_cn=common_name,
            o_mail=form.mail.data,
            o_loginshell='/bin/bash',
            o_gecos=gecos,
            fascreationtime=f"{now.isoformat()}Z",
            faslocale=guess_locale(),
            fastimezone=current_app.config["USER_DEFAULTS"]["timezone"],
            fasstatusnote=current_app.config["USER_DEFAULTS"]["status_note"],
        )['result']
        user = User(user)
    except python_freeipa.exceptions.DuplicateEntry:
        raise FormError(
            "non_field_errors",
            _(
                "The username '%(username)s' or the email address '%(email)s' are already taken.",
                username=username,
                email=form.mail.data,
            ),
        )
    except python_freeipa.exceptions.ValidationError as e:
        # for example: invalid username. We don't know which field to link it to
        _handle_registration_validation_error(username, e)
    except python_freeipa.exceptions.FreeIPAError as e:
        current_app.logger.error(
            f'An unhandled error {e.__class__.__name__} happened while registering user '
            f'{username}: {e.message}'
        )
        raise FormError(
            "non_field_errors",
            _('An error occurred while creating the account, please try again.'),
        )

    stageuser_created.send(user, request=request._get_current_object())
    if current_app.config["BASSET_URL"]:
        return redirect(f"{url_for('.spamcheck_wait')}?username={username}")
    else:
        # Send the address validation email
        _send_validation_email(user)
        return redirect(f"{url_for('.confirm_registration')}?username={username}")


@bp.route('/register/spamcheck-wait')
def spamcheck_wait():
    username = request.args.get('username')
    if not username:
        abort(400, "No username provided")

    try:
        user = User(ipa_admin.stageuser_show(a_uid=username)["result"])
    except python_freeipa.exceptions.NotFound:
        flash(_("The registration seems to have failed, please try again."), "warning")
        return redirect(f"{url_for('.root')}?tab=register")

    if user.status_note == "active":
        return redirect(f"{url_for('.confirm_registration')}?username={username}")

    return render_template('registration-spamcheck-wait.html', user=user)


@bp.route('/register/confirm', methods=["GET", "POST"])
def confirm_registration():
    username = request.args.get('username')
    if not username:
        abort(400, "No username provided")
    try:
        user = User(ipa_admin.stageuser_show(a_uid=username)['result'])
    except python_freeipa.exceptions.NotFound:
        flash(_("The registration seems to have failed, please try again."), "warning")
        return redirect(f"{url_for('.root')}?tab=register")

    if current_app.config["BASSET_URL"] and user.status_note != "active":
        abort(401, "You should not be here")

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


@bp.route('/register/activate', methods=["GET", "POST"])
def activate_account():
    register_url = f"{url_for('.root')}?tab=register"
    token_string = request.args.get('token')
    if not token_string:
        flash(
            _('No token provided, please check your email validation link.'), 'warning'
        )
        return redirect(register_url)

    try:
        token = read_token(token_string, audience=Audience.email_validation)
    except jwt.exceptions.DecodeError:
        flash(_("The token is invalid, please register again."), "warning")
        return redirect(register_url)
    except jwt.exceptions.ExpiredSignatureError:
        flash(_("This token is no longer valid, please register again."), "warning")
        return redirect(register_url)

    try:
        user = User(ipa_admin.stageuser_show(token["sub"])["result"])
    except python_freeipa.exceptions.NotFound:
        flash(_("This user cannot be found, please register again."), "warning")
        return redirect(register_url)

    token_mail = token["mail"]
    if not user.mail == token_mail:
        current_app.logger.error(
            f'User {user.username} tried to validate a token for address {token_mail} while they '
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
                current_app.logger.error(
                    f'An unhandled error {e.__class__.__name__} happened while activating '
                    f'stage user {user.username}: {e.message}'
                )
                raise FormError(
                    "non_field_errors",
                    _(
                        "Something went wrong while creating your account, "
                        "please try again later."
                    ),
                )
            # User activation succeeded. Send signal.
            user_registered.send(user, request=request._get_current_object())
            # Now we set the password.
            try:
                # First, set it as an admin. This will mark it as expired.
                ipa_admin.user_mod(user.username, userpassword=password)
                # And now we set it again as the user, so it is not expired any more.
                ipa = untouched_ipa_client(current_app)
                ipa.change_password(
                    user.username, new_password=password, old_password=password
                )
            except python_freeipa.exceptions.PWChangePolicyError as e:
                # The user is active but the password does not match the policy.
                # Tell the user what's going to happen.
                flash(
                    _(
                        'Your account has been created, but the password you chose does not '
                        'comply with the policy (%(policy_error)s) and has thus been set as '
                        'expired. You will be asked to change it after logging in.',
                        policy_error=e.policy_error,
                    ),
                    'warning',
                )
                return redirect(url_for(".root"))
            except python_freeipa.exceptions.ValidationError as e:
                # for example: invalid username. We don't know which field to link it to
                _handle_registration_validation_error(user.username, e)
            except python_freeipa.exceptions.FreeIPAError as e:
                current_app.logger.error(
                    f'An unhandled error {e.__class__.__name__} happened while changing initial '
                    f'password for user {user.username}: {e.message}'
                )
                # At this point the user has been activated, they can't register again. Send them to
                # the login page with an appropriate warning.
                flash(
                    _(
                        'Your account has been created, but an error occurred while setting your '
                        'password (%(message)s). You may need to change it after logging in.',
                        message=e.message,
                    ),
                    'warning',
                )
                return redirect(url_for(".root"))

            # Try to log them in directly, so they don't have to type their password again.
            try:
                ipa = maybe_ipa_login(current_app, session, user.username, password)
            except python_freeipa.exceptions.FreeIPAError:
                ipa = None
            if ipa:
                flash(
                    _(
                        'Congratulations, your account has been created! Welcome, %(name)s.',
                        name=user.name,
                    ),
                    'success',
                )
            else:
                # No shortcut for you, you'll have to login properly (maybe the password is
                # expired).
                flash(
                    _(
                        'Congratulations, your account has been created! Go ahead and sign in '
                        'to proceed.'
                    ),
                    'success',
                )
            return redirect(url_for('.root'))

    return render_template('registration-activation.html', user=user, form=form)


@bp.route('/register/spamcheck-hook', methods=["POST"])
@csrf.exempt
def spamcheck_hook():
    if not current_app.config.get("BASSET_URL"):
        return jsonify({"error": "Spamcheck disabled"}), 501

    data = request.get_json()
    if not data:
        return jsonify({"error": "Bad payload"}), 400

    try:
        token = data["token"]
        status = data["status"]
    except KeyError as e:
        return jsonify({"error": f"Missing key: {e}"}), 400

    try:
        token_data = read_token(token, audience=Audience.spam_check)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "The token has expired"}), 400
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 400

    username = token_data["sub"]

    if status not in ("active", "spamcheck_denied", "spamcheck_manual"):
        return jsonify({"error": f"Invalid status: {status}."}), 400
    result = ipa_admin.stageuser_mod(a_uid=username, fasstatusnote=status)
    user = User(result["result"])

    if status == "active":
        # Send the address validation email
        _send_validation_email(user)

    return jsonify({"status": "success"})


@bp.route('/registering/', methods=["GET", "POST"])
@with_ipa()
def registering_users(ipa):
    stage_users = ipa.stageuser_find()["result"]
    stage_users = [User(su) for su in stage_users]

    statuses = [
        {"name": "", "title": _("All")},
        {"name": "spamcheck_manual", "title": _("Unknown")},
        {"name": "active", "title": _("Not Spam")},
        {"name": "spamcheck_denied", "title": _("Spam")},
        {"name": "spamcheck_awaiting", "title": _("Awaiting")},
    ]
    for status in statuses:
        status["count"] = len(
            [
                su
                for su in stage_users
                if status["name"] == "" or su.status_note == status["name"]
            ]
        )

    status_filter = request.args.get("status", "")
    if status_filter:
        stage_users = [su for su in stage_users if su.status_note == status_filter]
    stage_users.sort(key=lambda u: u.creation_time)
    stage_users.reverse()

    form = RegisteringActionForm()

    if form.validate_on_submit():
        username = form.username.data
        action = form.action.data
        try:
            user = [su for su in stage_users if su.username == username][0]
        except IndexError:
            flash(f"Unknown user: {username}", "danger")
            return redirect(request.url)

        if action == "accept":
            try:
                current_app.logger.info(f"Accepting registering user {username}")
                ipa.stageuser_mod(username, fasstatusnote="active")
                _send_validation_email(user)
            except Exception as e:
                form.non_field_errors.errors.append(
                    f"Could not accept registering user {username}: {e}"
                )
            else:
                flash(f"Accepted registering user {username}", "success")
                return redirect(request.url)

        elif action == "spam":
            try:
                current_app.logger.info(f"Flagging registering user {username} as spam")
                ipa.stageuser_mod(username, fasstatusnote="spamcheck_denied")
            except Exception as e:
                form.non_field_errors.errors.append(
                    f"Could not flag registering user {username} as spam: {e}"
                )
            else:
                flash(f"Flagged registering user {username} as spam", "success")
                return redirect(request.url)

        elif action == "delete":
            try:
                current_app.logger.info(f"Deleting registering user {username}")
                ipa.stageuser_del(username)
            except Exception as e:
                form.non_field_errors.errors.append(
                    f"Could not delete registering user {username}: {e}"
                )
            else:
                flash(f"Deleted registering user {username}", "success")
                return redirect(request.url)

        else:
            form.non_field_errors.errors.append(f"Invalid action: {action}")

    return render_template(
        "registering.html",
        statuses=statuses,
        stage_users=stage_users,
        form=form,
        filter=status_filter,
    )
