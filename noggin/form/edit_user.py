from flask_babel import lazy_gettext as _
from pyotp import TOTP
from wtforms import (
    BooleanField,
    FieldList,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.fields.html5 import EmailField, URLField
from wtforms.validators import (
    AnyOf,
    DataRequired,
    Length,
    Optional,
    URL,
    ValidationError,
)

from noggin.form.validators import Email
from noggin.l10n import LOCALES
from noggin.utility.timezones import TIMEZONES

from .base import BaseForm, CSVListField, ModestForm, strip, SubmitButtonField


class UserSettingsProfileForm(BaseForm):
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
            Email(message=_('Email must be valid')),
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

    is_private = BooleanField(
        _('Private'),
        description=_(
            "Hide information from other users, see the Privacy Policy for details."
        ),
        validators=[Optional()],
    )

    pronouns = StringField(_('Pronouns'), validators=[Optional()],)


class UserSettingsKeysForm(BaseForm):
    sshpubkeys = FieldList(
        TextAreaField(validators=[Optional()], render_kw={"rows": 4}, filters=[strip]),
        label=_('SSH Keys'),
    )

    gpgkeys = FieldList(
        StringField(validators=[Optional(), Length(min=16, max=40)]),
        label=_('GPG Keys'),
    )


class UserSettingsAddOTPForm(ModestForm):
    description = StringField(
        _('Token name'),
        validators=[Optional()],
        description=_("Add an optional name to help you identify this token"),
    )

    password = PasswordField(
        _('Enter your current password'),
        validators=[DataRequired(message=_('You must provide a password'))],
        description=_("please reauthenticate so we know it is you"),
    )

    otp = StringField(
        _('One-Time Password'),
        validators=[Optional()],
        description=_("Enter your One-Time Password"),
    )

    submit = SubmitButtonField(_("Generate OTP Token"))


class UserSettingsConfirmOTPForm(ModestForm):
    secret = HiddenField(
        "secret",
        validators=[DataRequired(message=_('Could not find the token secret'))],
    )
    description = HiddenField("description", validators=[Optional()],)
    code = StringField(
        _("Verification Code"),
        validators=[DataRequired(message=_('You must provide a verification code'))],
    )
    submit = SubmitButtonField(_("Verify and Enable OTP Token"))

    def validate_code(form, field):
        totp = TOTP(form.secret.data)
        if not totp.verify(field.data, valid_window=1):
            raise ValidationError(_('The code is wrong, please try again.'))


class UserSettingsOTPStatusChange(BaseForm):
    token = HiddenField(
        'token', validators=[DataRequired(message=_('Token must not be empty'))]
    )


class UserSettingsAgreementSign(BaseForm):
    agreement = HiddenField(
        'agreement', validators=[DataRequired(message=_('Agreement must not be empty'))]
    )
