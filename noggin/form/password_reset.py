from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length

from noggin import app


class NewPasswordForm(FlaskForm):

    password = PasswordField(
        _('New Password'),
        validators=[
            DataRequired(message=_('Password must not be empty')),
            Length(
                min=app.config["PASSWORD_POLICY"].get("min", -1),
                max=app.config["PASSWORD_POLICY"].get("max", -1),
            ),
            EqualTo('password_confirm', message=_('Passwords must match')),
        ],
    )

    password_confirm = PasswordField(_('Confirm New Password'))

    otp = StringField(
        _('OTP Token'), description=_("Enter your OTP token if you have enrolled one")
    )


class PasswordResetForm(NewPasswordForm):

    current_password = PasswordField(
        _('Current Password'),
        validators=[DataRequired(message=_('Current password must not be empty'))],
        description=_("Just the password, don't add the OTP token if you have one"),
    )


class ForgottenPasswordForm(FlaskForm):

    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('User name must not be empty'))],
        description=_("Enter your username to reset your password"),
    )
