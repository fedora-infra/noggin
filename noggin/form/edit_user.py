from flask_babel import lazy_gettext as _
from wtforms import (
    FieldList,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.fields.html5 import EmailField, URLField
from wtforms.validators import AnyOf, DataRequired, Length, Optional, URL

from noggin import app
from noggin.form.validators import Email
from noggin.utility.locales import LOCALES
from noggin.utility.timezones import TIMEZONES

from .base import BaseForm, CSVListField


class UserSettingsProfileForm(BaseForm):
    firstname = StringField(
        _('First Name'),
        validators=[Optional()],
    )

    lastname = StringField(
        _('Last Name'),
        validators=[Optional()],
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

    website_url = URLField(
        _('Website or Blog URL'),
        validators=[Optional(), URL(message=_('Valid URL required'))],
    )


class UserSettingsKeysForm(BaseForm):
    sshpubkeys = FieldList(
        TextAreaField(validators=[Optional()], render_kw={"rows": 4}),
        label=_('SSH Keys'),
    )

    gpgkeys = FieldList(
        StringField(validators=[Optional(), Length(max=16)]), label=_('GPG Keys')
    )


class UserSettingsAddOTPForm(BaseForm):
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


class UserSettingsOTPStatusChange(BaseForm):
    token = HiddenField(
        'token', validators=[DataRequired(message=_('token must not be empty'))]
    )


class UserSettingsAgreementSign(BaseForm):
    agreement = HiddenField(
        'agreement', validators=[DataRequired(message=_('agreement must not be empty'))]
    )
