from urllib.parse import urlparse, quote

from flask import flash, redirect, render_template, session, url_for, Markup
from flask_babel import _
import python_freeipa

from noggin import app
from noggin.form.edit_user import (
    UserSettingsProfileForm,
    UserSettingsKeysForm,
    UserSettingsAddOTPForm,
    UserSettingsOTPStatusChange,
)
from noggin.representation.group import Group
from noggin.representation.user import User
from noggin.representation.otptoken import OTPToken
from noggin.security.ipa import maybe_ipa_login
from noggin.utility import (
    with_ipa,
    user_or_404,
    FormError,
    handle_form_errors,
    require_self,
)


@app.route('/user/<username>/')
@with_ipa(app, session)
def user(ipa, username):
    user = User(user_or_404(ipa, username))
    # As a speed optimization, we make two separate calls.
    # Just doing a group_find (with all=True) is super slow here, with a lot of
    # groups.
    member_groups = [
        Group(g)
        for g in ipa.group_find(user=username, all=False, fasgroup=True)['result']
    ]
    managed_groups = [
        Group(g)
        for g in ipa.group_find(membermanager_user=username, all=False, fasgroup=True)[
            'result'
        ]
    ]
    groups = [g for g in managed_groups if g not in member_groups] + member_groups

    return render_template(
        'user.html',
        user=user,
        groups=groups,
        managed_groups=managed_groups,
        member_groups=member_groups,
    )


def _user_mod(ipa, form, username, details, redirect_to):
    with handle_form_errors(form):
        try:
            ipa.user_mod(username, **details)
        except python_freeipa.exceptions.BadRequest as e:
            if e.message == 'no modifications to be performed':
                raise FormError("non_field_errors", e.message)
            else:
                app.logger.error(
                    f'An error happened while editing user {username}: {e.message}'
                )
                raise FormError("non_field_errors", e.message)
        flash(
            Markup(
                f'Profile Updated: <a href=\"{url_for("user", username=username)}\">'
                'view your profile</a>'
            ),
            'success',
        )
        return redirect(url_for(redirect_to, username=username))


@app.route('/user/<username>/settings/profile/', methods=['GET', 'POST'])
@with_ipa(app, session)
@require_self
def user_settings_profile(ipa, username):
    user = User(user_or_404(ipa, username))
    form = UserSettingsProfileForm(obj=user)

    if form.validate_on_submit():
        result = _user_mod(
            ipa,
            form,
            username,
            {
                'first_name': form.firstname.data,
                'last_name': form.lastname.data,
                'full_name': '%s %s' % (form.firstname.data, form.lastname.data),
                'display_name': '%s %s' % (form.firstname.data, form.lastname.data),
                'mail': form.mail.data,
                'fasircnick': form.ircnick.data,
                'faslocale': form.locale.data,
                'fastimezone': form.timezone.data,
                'fasgithubusername': form.github.data.lstrip('@'),
                'fasgitlabusername': form.gitlab.data.lstrip('@'),
                'fasrhbzemail': form.rhbz_mail.data,
            },
            "user_settings_profile",
        )
        if result:
            return result

    return render_template(
        'user-settings-profile.html', user=user, form=form, activetab="profile"
    )


@app.route('/user/<username>/settings/keys/', methods=['GET', 'POST'])
@with_ipa(app, session)
@require_self
def user_settings_keys(ipa, username):
    user = User(user_or_404(ipa, username))
    form = UserSettingsKeysForm(obj=user)

    if form.validate_on_submit():
        result = _user_mod(
            ipa,
            form,
            username,
            {'ipasshpubkey': form.sshpubkeys.data, 'fasgpgkeyid': form.gpgkeys.data},
            "user_settings_keys",
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


@app.route('/user/<username>/settings/otp/', methods=['GET', 'POST'])
@with_ipa(app, session)
@require_self
def user_settings_otp(ipa, username):
    addotpform = UserSettingsAddOTPForm()
    user = User(user_or_404(ipa, username))

    if addotpform.validate_on_submit():
        try:
            maybe_ipa_login(app, session, username, addotpform.password.data)
            result = ipa.otptoken_add(
                ipatokenowner=username,
                ipatokenotpalgorithm='sha512',
                description=addotpform.description.data,
            )
            uri = urlparse(result["uri"])
            # Use the provided description in the token, so it shows up in the user's app instead of
            # the token's UUID
            principal = uri.path.split(":", 1)[0]
            new_uri = uri._replace(
                path=f"{principal.lower()}:{quote(addotpform.description.data)}"
            )
            session['otp_uri'] = new_uri.geturl()
        except python_freeipa.exceptions.InvalidSessionPassword:
            addotpform.password.errors.append(_("Incorrect password"))
        except python_freeipa.exceptions.FreeIPAError as e:
            app.logger.error(
                f'An error happened while creating an OTP token for user {username}: {e.message}'
            )
            addotpform.errors['non_field_errors'] = [_('Cannot create the token.')]
        else:
            return redirect(url_for('user_settings_otp', username=username))

    otp_uri = session.get('otp_uri')
    session['otp_uri'] = None

    tokens = [OTPToken(t) for t in ipa.otptoken_find(ipatokenowner=username)]
    tokens.sort(key=lambda t: t.description or "")

    return render_template(
        'user-settings-otp.html',
        addotpform=addotpform,
        user=user,
        activetab="otp",
        tokens=tokens,
        otp_uri=otp_uri,
    )


@app.route('/user/<username>/settings/otp/disable/', methods=['POST'])
@with_ipa(app, session)
@require_self
def user_settings_otp_disable(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        token = form.token.data
        try:
            ipa.otptoken_mod(ipatokenuniqueid=token, ipatokendisabled=True)
        except python_freeipa.exceptions.BadRequest as e:
            if (
                e.message
                == "Server is unwilling to perform: Can't disable last active token"
            ):
                flash(_('Sorry, You cannot disable your last active token.'), 'warning')
            else:
                flash('Cannot disable the token.', 'danger')
                app.logger.error(
                    f'Something went wrong disabling an OTP token for user {username}: {e}'
                )
        except python_freeipa.exceptions.FreeIPAError as e:
            flash(_('Cannot disable the token.'), 'danger')
            app.logger.error(
                f'Something went wrong disabling an OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('user_settings_otp', username=username))


@app.route('/user/<username>/settings/otp/enable/', methods=['POST'])
@with_ipa(app, session)
@require_self
def user_settings_otp_enable(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        token = form.token.data
        try:
            ipa.otptoken_mod(ipatokenuniqueid=token, ipatokendisabled=None)
        except (
            python_freeipa.exceptions.BadRequest,
            python_freeipa.exceptions.FreeIPAError,
        ) as e:
            flash(
                _('Cannot enable the token. %(errormessage)s', errormessage=e), 'danger'
            )
            app.logger.error(
                f'Something went wrong enabling an OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('user_settings_otp', username=username))


@app.route('/user/<username>/settings/otp/delete/', methods=['POST'])
@with_ipa(app, session)
@require_self
def user_settings_otp_delete(ipa, username):
    form = UserSettingsOTPStatusChange()

    if form.validate_on_submit():
        username = session.get('noggin_username')
        token = form.token.data
        try:
            ipa.otptoken_del(ipatokenuniqueid=token)
        except python_freeipa.exceptions.BadRequest as e:
            if (
                e.message
                == "Server is unwilling to perform: Can't delete last active token"
            ):
                flash(_('Sorry, You cannot delete your last active token.'), 'warning')
            else:
                flash(_('Cannot delete the token.'), 'danger')
                app.logger.error(
                    f'Something went wrong deleting OTP token for user {username}: {e}'
                )
        except python_freeipa.exceptions.FreeIPAError as e:
            flash(_('Cannot delete the token.'), 'danger')
            app.logger.error(
                f'Something went wrong deleting OTP token for user {username}: {e}'
            )

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('user_settings_otp', username=username))
