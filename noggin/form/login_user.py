from flask_babel import lazy_gettext as _
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Optional

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

    otp = StringField(_('One-Time Password'), validators=[Optional()])

    submit = SubmitButtonField(_('Log In'))
