from flask_babel import lazy_gettext as _
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired

from .base import ModestForm, SubmitButtonField


class LoginUserForm(ModestForm):
    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('You must provide a user name'))],
    )

    password = PasswordField(
        _('Password'),
        validators=[DataRequired(message=_('You must provide a password'))],
    )

    otp = PasswordField(
        _('One-Time-Password'),
    )

    submit = SubmitButtonField(_('Log In'))
