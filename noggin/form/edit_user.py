from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _
from wtforms import (
    FieldList,
    StringField,
    SelectField,
    TextAreaField,
    HiddenField,
    PasswordField,
)

from wtforms.fields.html5 import EmailField
from wtforms.validators import AnyOf, DataRequired, Optional, Length

from noggin import app
from noggin.form.validators import Email
from noggin.utility.locales import LOCALES
from noggin.utility.timezones import TIMEZONES
from .base import CSVListField


class UserSettingsProfileForm(FlaskForm):
    firstname = StringField(
        _('First Name'),
        validators=[DataRequired(message=_('First name must not be empty'))],
    )

    lastname = StringField(
        _('Last Name'),
        validators=[DataRequired(message=_('Last name must not be empty'))],
    )

    mail = EmailField(
        _('E-mail Address'),
        validators=[
            DataRequired(message=_('Email must not be empty')),
            Email(
                message=_('Email must be valid'),
                blocklist=app.config["MAIL_DOMAIN_BLOCKLIST"],
            ),
        ],
    )

    locale = SelectField(
        _('Locale'),
        choices=[(locale, locale) for locale in LOCALES],
        validators=[
            DataRequired(message=_('Locale must not be empty')),
            AnyOf(LOCALES, message=_('Locale must be a valid locale short-code')),
        ],
    )

    ircnick = CSVListField(_('IRC Nicknames'), validators=[Optional()])

    timezone = SelectField(
        _('Timezone'),
        choices=[(t, t) for t in TIMEZONES],
        validators=[
            DataRequired(message=_('Timezone must not be empty')),
            AnyOf(TIMEZONES, message=_('Timezone must be a valid timezone')),
        ],
    )

    github = StringField(_('GitHub Username'), validators=[Optional()])

    gitlab = StringField(_('GitLab Username'), validators=[Optional()])

    rhbz_mail = EmailField(_('Red Hat Bugzilla Email'), validators=[Optional()])


class UserSettingsKeysForm(FlaskForm):
    sshpubkeys = FieldList(
        TextAreaField(validators=[Optional()], render_kw={"rows": 4}),
        label=_('SSH Keys'),
    )

    gpgkeys = FieldList(
        StringField(validators=[Optional(), Length(max=16)]), label=_('GPG Keys')
    )


class UserSettingsAddOTPForm(FlaskForm):
    description = StringField(
        _('Token name'),
        validators=[Optional()],
        description=_("add an optional name to help you identify this token"),
    )

    password = PasswordField(
        _('Enter your current password'),
        validators=[DataRequired(message=_('You must provide a password'))],
        description=_("please reauthenticate so we know it is you"),
    )


class UserSettingsOTPStatusChange(FlaskForm):
    token = HiddenField(
        'token', validators=[DataRequired(message=_('token must not be empty'))]
    )
