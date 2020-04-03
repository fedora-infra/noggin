from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo, Email

from .base import ModestForm, SubmitButtonField, strip


class RegisterUserForm(ModestForm):
    firstname = StringField(
        _('First Name'),
        validators=[DataRequired(message=_('First name must not be empty'))],
        filters=[strip],
    )

    lastname = StringField(
        _('Last Name'),
        validators=[DataRequired(message=_('Last name must not be empty'))],
        filters=[strip],
    )

    username = StringField(
        _('Username'),
        validators=[DataRequired(message=_('User name must not be empty'))],
        filters=[strip],
    )

    mail = EmailField(
        _('E-mail Address'),
        validators=[
            DataRequired(message=_('Email must not be empty')),
            Email(message=_('Email must be valid')),
        ],
        filters=[strip],
    )

    submit = SubmitButtonField(_("Register"))


class ResendValidationEmailForm(FlaskForm):
    submit = SubmitButtonField(_("Resend email"))


class PasswordSetForm(FlaskForm):

    password = PasswordField(
        _('Password'),
        validators=[
            DataRequired(message=_('Password must not be empty')),
            EqualTo('password_confirm', message=_('Passwords must match')),
        ],
        filters=[strip],
        description=_("Please choose a strong password"),
    )

    password_confirm = PasswordField(_('Confirm Password'), filters=[strip])

    submit = SubmitButtonField(_("Activate"))
