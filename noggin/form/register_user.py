from flask_babel import lazy_gettext as _
from wtforms.fields import (
    BooleanField,
    EmailField,
    HiddenField,
    PasswordField,
    StringField,
)
from wtforms.validators import DataRequired, EqualTo, Length

from noggin.form.validators import Email, PasswordLength, StopOnError, username_format

from .base import BaseForm, ModestForm, strip, SubmitButtonField


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
        validators=[
            DataRequired(message=_('User name must not be empty')),
            StopOnError(Length(min=3, max=32)),
            username_format,
        ],
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

    underage = BooleanField(
        _('I am over 16 years old'),
        validators=[
            DataRequired(
                message=_("You must be over 16 years old to create an account")
            )
        ],
    )

    submit = SubmitButtonField(_("Register"))


class ResendValidationEmailForm(BaseForm):
    submit = SubmitButtonField(_("Resend email"))


class PasswordSetForm(BaseForm):

    password = PasswordField(
        _('Password'),
        validators=[
            DataRequired(message=_('Password must not be empty')),
            PasswordLength(),
            EqualTo('password_confirm', message=_('Passwords must match')),
        ],
        filters=[strip],
        description=_("Please choose a strong password"),
    )

    password_confirm = PasswordField(_('Confirm Password'), filters=[strip])

    submit = SubmitButtonField(_("Activate"))


class RegisteringActionForm(BaseForm):
    username = HiddenField(validators=[DataRequired()])
    action = StringField(validators=[DataRequired()])
