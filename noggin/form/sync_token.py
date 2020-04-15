from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Optional


class SyncTokenForm(FlaskForm):
    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('You must provide a user name'))],
    )

    password = PasswordField(
        _('Password'),
        validators=[DataRequired(message=_('You must provide a password'))],
    )

    first_code = StringField(
        _('First OTP'),
        validators=[DataRequired(message=_('You must provide a first code'))],
    )

    second_code = StringField(
        _('Second OTP'),
        validators=[DataRequired(message=_('You must provide a second code'))],
    )

    token = StringField(_('Token ID'), validators=[Optional()])
