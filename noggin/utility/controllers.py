from functools import wraps
from urllib.parse import quote

import python_freeipa
from flask import abort, current_app, flash, g, redirect, request, session, url_for
from flask_babel import lazy_gettext as _

from noggin.app import ipa_admin
from noggin.representation.user import User
from noggin.security.ipa import maybe_ipa_session


def is_role_member(role_result, username, user_groups=None):
    """Check if a user is a member of an IPA role (directly or via group)."""
    result = role_result.get('result', {})
    if username in result.get('member_user', []):
        return True
    if user_groups:
        role_groups = set(result.get('member_group', []))
        if role_groups.intersection(user_groups):
            return True
    return False


# A wrapper that will give us 'ipa' if it exists, or bump the user back to /
# with a message telling them to log in.
def with_ipa():
    def decorator(f):
        @wraps(f)
        def fn(*args, **kwargs):
            ipa = maybe_ipa_session(current_app, session)
            if ipa:
                g.ipa = ipa
                g.current_user = User(g.ipa.user_find(whoami=True)['result'][0])
                return f(*args, **kwargs, ipa=ipa)
            coming_from = quote(request.full_path)
            flash(_('Please log in to continue.'), 'warning')
            return redirect(f"{url_for('.root')}?next={coming_from}")

        return fn

    return decorator


def require_self(f):
    """Require the logged-in user to be the user that is currently being edited"""

    @wraps(f)
    def fn(*args, **kwargs):
        try:
            username = kwargs["username"]
        except KeyError:
            abort(
                500,
                "The require_self decorator only works on routes that have 'username' "
                "as a component.",
            )
        if session.get('noggin_username') != username:
            flash(_('You do not have permission to edit this account.'), 'danger')
            return redirect(url_for('.user', username=username))
        return f(*args, **kwargs)

    return fn


def require_otp_admin(f):
    """Require the logged-in user to be an OTP recovery admin for the target user."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        role = current_app.config.get('OTP_ADMIN_RECOVERY_ROLE')
        if not role:
            abort(404)
        current_username = session.get('noggin_username')
        target_username = kwargs.get('username')
        if current_username == target_username:
            return redirect(
                url_for('.user_settings_otp', username=target_username)
            )
        try:
            role_info = ipa_admin.role_show(a_cn=role)
            user_groups = getattr(g.current_user, 'groups', None)
            if not is_role_member(role_info, current_username, user_groups):
                flash(
                    _('You do not have permission to reset OTP for this user.'),
                    'danger',
                )
                return redirect(url_for('.user', username=target_username))
        except python_freeipa.exceptions.FreeIPAError:
            current_app.logger.warning(
                'Failed to check OTP admin role %s for user %s',
                role,
                current_username,
            )
            flash(
                _(
                    'Could not verify your permissions. '
                    'Please try again later.'
                ),
                'danger',
            )
            return redirect(url_for('.user', username=target_username))
        return f(*args, **kwargs)

    return wrapper


def group_or_404(ipa, groupname):
    group = ipa.group_find(o_cn=groupname, fasgroup=True)['result']
    if not group:
        abort(404, _('Group %(groupname)s could not be found.', groupname=groupname))
    else:
        return group[0]


def user_or_404(ipa, username):
    try:
        user = ipa.user_show(a_uid=username)['result']
    except python_freeipa.exceptions.NotFound:
        abort(404)
    if User(user).locked:
        abort(404)
    return user


def get_username_from_email(ipa, username_or_email):
    if "@" not in username_or_email:
        return username_or_email

    result = ipa.user_find(o_mail=username_or_email)['result']
    if not result:
        msg = _(
            "No Users with email %(username_or_email)s found",
            username_or_email=username_or_email,
        )
        current_app.logger.info(msg)
        raise ValueError(msg)
    return result[0]["uid"][0]
