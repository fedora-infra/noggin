import jwt
import python_freeipa
from flask import (
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import _
from flask_mail import Message
from markupsafe import Markup

from noggin.app import mailer
from noggin.form.base import BaseForm
from noggin.form.edit_user import (
    UserSettingsAgreementSign,
    UserSettingsEmailForm,
    UserSettingsKeysForm,
    UserSettingsProfileForm,
)
from noggin.representation.agreement import Agreement
from noggin.representation.group import Group
from noggin.representation.user import User
from noggin.utility import messaging
from noggin.utility.controllers import require_self, user_or_404, with_ipa
from noggin.utility.forms import FormError, handle_form_errors
from noggin.utility.token import Audience, make_token, read_token
from noggin_messages import UserUpdateV1

from . import blueprint as bp


@bp.route('/user/<username>/')
@with_ipa()
def user(ipa, username):
    user = User(user_or_404(ipa, username))
    # As a speed optimization, we make two separate calls.
    # Just doing a group_find (with all=True) is super slow here, with a lot of
    # groups.
    batch_methods = [
        {"method": "group_show", "params": [[name], {"no_members": True}]}
        for name in user.groups
    ]
    # Don't call remote batch method with an empty list
    if batch_methods:
        member_groups = [
            Group(g["result"])
            for g in ipa.batch(batch_methods)["results"]
            if g["result"].get("fasgroup", False)
        ]
    else:
        member_groups = []

    managed_groups = [
        Group(group)
        for group in ipa.group_find(
            o_membermanager_user=username, o_all=False, fasgroup=True
        )['result']
    ]
    groups = sorted(list(set(managed_groups + member_groups)), key=lambda g: g.name)

    # Privacy setting
    if user != g.current_user and user.is_private:
        user.anonymize()

    return render_template(
        'user.html',
        user=user,
        groups=groups,
        managed_groups=managed_groups,
        member_groups=member_groups,
    )


def _user_mod(ipa, form, user, details, redirect_to):
    with handle_form_errors(form):
        try:
            updated_user = User(
                ipa.user_mod(user.username, **details, all=True)['result']
            )
        except python_freeipa.exceptions.BadRequest as e:
            if e.message == 'no modifications to be performed':
                raise FormError("non_field_errors", e.message)
            else:
                current_app.logger.error(
                    f'An error happened while editing user {user.username}: {e.message}'
                )
                raise FormError("non_field_errors", e.message)
        flash(
            Markup(
                _(
                    'Profile Updated: <a href="%(url)s">view your profile</a>',
                    url=url_for(".user", username=user.username),
                )
            ),
            'success',
        )

        messaging.publish(
            UserUpdateV1(
                {
                    "msg": {
                        "agent": user.username,
                        "user": user.username,
                        "fields": user.diff_fields(updated_user),
                    }
                }
            )
        )

        return redirect(url_for(redirect_to, username=user.username))


@bp.route('/user/<username>/settings/profile/', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_profile(ipa, username):
    user = User(user_or_404(ipa, username))
    form = UserSettingsProfileForm(obj=user)

    if form.validate_on_submit():
        changes = {
            user.get_attr_option(field.short_name): getattr(form, field.short_name).data
            for field in form
            if field.short_name in user
        }
        fullname = f"{form.firstname.data} {form.lastname.data}"
        changes["o_cn"] = changes["o_displayname"] = changes["o_gecos"] = fullname
        result = _user_mod(
            ipa,
            form,
            user,
            changes,
            ".user_settings_profile",
        )
        if result:
            return result
    # Add empty field at the end of field lists
    if not form.errors:
        for field in form:
            if field.type == "FieldList":
                field.append_entry()

    return render_template(
        'user-settings-profile.html', user=user, form=form, activetab="profile"
    )


def _send_validation_email(user, attr, value):
    token = make_token(
        {"sub": user.username, "attr": attr, "mail": value},
        audience=Audience.email_validation,
        ttl=current_app.config["ACTIVATION_TOKEN_EXPIRATION"],
    )
    email_context = {"token": token, "user": user, "address": value}
    email = Message(
        body=render_template("settings-email-validation.txt", **email_context),
        html=render_template("settings-email-validation.html", **email_context),
        recipients=[value],
        subject=_("Verify your email address"),
    )
    if current_app.config["DEBUG"]:  # pragma: no cover
        current_app.logger.debug(email)
    mailer.send(email)


@bp.route('/user/<username>/settings/email/', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_email(ipa, username):
    user = User(user_or_404(ipa, username))
    form = UserSettingsEmailForm(obj=user)
    attrs = ["mail", "rhbz_mail"]

    if form.validate_on_submit():
        change_now = {}
        needs_validation = {}
        for attr in attrs:
            value = getattr(form, attr).data
            old_value = getattr(user, attr) or ""
            option_name = user.get_attr_option(attr)
            if value != old_value:
                if not value:
                    # email has been removed
                    change_now[option_name] = value
                else:
                    needs_validation[attr] = value
        should_redirect = False
        if change_now:
            should_redirect = _user_mod(
                ipa,
                form,
                user,
                change_now,
                ".user_settings_email",
            )
        if needs_validation:
            for attr, value in needs_validation.items():
                try:
                    _send_validation_email(user, attr, value)
                except ConnectionRefusedError as e:
                    current_app.logger.error(
                        f"Impossible to send an address validation email: {e}"
                    )
                    form["non_field_errors"].errors.append(
                        _(
                            "We could not send you the address validation email, please retry later"
                        )
                    )
                    break
                flash(
                    _(
                        "The email address %(mail)s needs to be validated. Please check your "
                        "inbox and click on the link to proceed. If you can't find the email "
                        "in a couple minutes, check your spam folder.",
                        mail=value,
                    ),
                    "info",
                )
                should_redirect = redirect(
                    url_for('.user_settings_email', username=user.username)
                )
        if should_redirect:
            return should_redirect
        if not change_now and not needs_validation:
            form["non_field_errors"].errors.append(_("No modifications."))

    return render_template(
        'user-settings-email.html', user=user, form=form, activetab="email"
    )


@bp.route('/user/<username>/settings/email/validate', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_email_validate(ipa, username):
    user = User(user_or_404(ipa, username))

    url = url_for('.user_settings_email', username=user.username)
    token_string = request.args.get('token')

    if not token_string:
        flash(
            _('No token provided, please check your email validation link.'), 'warning'
        )
        return redirect(url)

    try:
        token = read_token(token_string, audience=Audience.email_validation)
    except jwt.exceptions.DecodeError:
        flash(_("The token is invalid, please set the email again."), "warning")
        return redirect(url)
    except jwt.exceptions.ExpiredSignatureError:
        flash(
            _("This token is no longer valid, please set the email again."), "warning"
        )
        return redirect(url)
    if token["sub"] != user.username:
        flash(_("This token does not belong to you."), "warning")
        return redirect(url)

    attr = token["attr"]
    value = token["mail"]
    form = BaseForm()

    if form.validate_on_submit():
        option_name = user.get_attr_option(token["attr"])
        result = _user_mod(
            ipa,
            form,
            user,
            {option_name: value},
            ".user_settings_email",
        )
        if result:
            return result

    return render_template(
        'user-settings-email-validation.html',
        form=form,
        user=user,
        attr_label=UserSettingsEmailForm()[attr].label,
        value=value,
    )


@bp.route('/user/<username>/settings/keys/', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_keys(ipa, username):
    user = User(user_or_404(ipa, username))
    form = UserSettingsKeysForm(obj=user)

    if form.validate_on_submit():
        result = _user_mod(
            ipa,
            form,
            user,
            {'o_ipasshpubkey': form.sshpubkeys.data, 'fasgpgkeyid': form.gpgkeys.data},
            ".user_settings_keys",
        )
        if result:
            return result

    # if the form has errors, we don't want to add new fields. otherwise,
    # more fields will show up with every validation error
    if not form.errors:
        # Append 2 empty entries at the bottom of the gpgkeys fieldlist
        for i in range(2):
            form.gpgkeys.append_entry()
            form.sshpubkeys.append_entry()

    return render_template(
        'user-settings-keys.html', user=user, form=form, activetab="keys"
    )


def handle_agreement_form(ipa, user, form):
    agreement_name = form.agreement.data
    try:
        ipa.fasagreement_add_user(agreement_name, user=user.username)
    except python_freeipa.exceptions.BadRequest as e:
        current_app.logger.error(f"Cannot sign the agreement {agreement_name!r}: {e}")
        flash(
            _(
                'Cannot sign the agreement "%(name)s": %(error)s',
                name=agreement_name,
                error=e,
            ),
            'danger',
        )
    else:
        flash(
            _('You signed the "%(name)s" agreement.', name=agreement_name),
            "success",
        )
    return redirect(request.url)


@bp.route('/user/<username>/settings/agreements/', methods=['GET', 'POST'])
@with_ipa()
@require_self
def user_settings_agreements(ipa, username):
    user = User(user_or_404(ipa, username))
    agreements = [
        Agreement(a) for a in ipa.fasagreement_find(all=False, ipaenabledflag=True)
    ]
    form = UserSettingsAgreementSign()
    if form.validate_on_submit():
        return handle_agreement_form(ipa, user, form)

    return render_template(
        'user-settings-agreements.html',
        user=user,
        activetab="agreements",
        agreementslist=agreements,
        raw=ipa.fasagreement_find(all=True),
    )
