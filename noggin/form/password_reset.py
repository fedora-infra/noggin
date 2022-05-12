from flask_babel import lazy_gettext as _
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Optional

from .base import BaseForm, lower
from .validators import PasswordLength


class NewPasswordForm(BaseForm):

    password = PasswordField(
        _('New Password'),
        validators=[
            DataRequired(message=_('Password must not be empty')),
            PasswordLength(),
            EqualTo('password_confirm', message=_('Passwords must match')),
        ],
    )

    password_confirm = PasswordField(_('Confirm New Password'))

    otp = StringField(
        _('One-Time Password (if your account has Two-Factor Authentication enabled)'),
        validators=[Optional()],
    )


class PasswordResetForm(NewPasswordForm):

    current_password = PasswordField(
        _('Current Password'),
        validators=[DataRequired(message=_('Current password must not be empty'))],
    )


class ForgottenPasswordForm(BaseForm):

    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('User name must not be empty'))],
        description=_("Enter your username to reset your password"),
        filters=[lower],
    )
