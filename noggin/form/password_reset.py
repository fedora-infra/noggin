from flask_babel import lazy_gettext as _
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Optional

from .base import BaseForm
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

    otp = PasswordField(
        _('One-Time Password'),
        validators=[Optional()],
        description=_("Enter your One-Time Password (if you have one)"),
    )


class PasswordResetForm(NewPasswordForm):

    current_password = PasswordField(
        _('Current Password'),
        validators=[DataRequired(message=_('Current password must not be empty'))],
        description=_("Just the password, don't add the OTP token if you have one"),
    )


class ForgottenPasswordForm(BaseForm):

    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('User name must not be empty'))],
        description=_("Enter your username to reset your password"),
    )
