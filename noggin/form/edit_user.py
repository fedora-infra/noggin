import re
from urllib.parse import urlparse, urlunparse

from flask_babel import lazy_gettext as _
from pyotp import TOTP
from wtforms.fields import (
    BooleanField,
    EmailField,
    FieldList,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
    URLField,
)
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

from .base import (
    BaseForm,
    CSVListField,
    ModestForm,
    NonEmptyFieldList,
    replace,
    strip,
    strip_at,
    SubmitButtonField,
    TypeAndStringField,
)


NICK_RE = {
    "irc": re.compile(r"^[a-z_\[\]\\^{}|`-][a-z0-9_\[\]\\^{}|`-]*$", re.IGNORECASE),
    "matrix": re.compile(r"^[a-z0-9.=_/-]+$", re.IGNORECASE),
}
SERVER_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*(:[0-9]+)?$", re.IGNORECASE)


class ProtocolAndNickField(TypeAndStringField):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [("irc", "IRC"), ("matrix", "Matrix")]
        kwargs["filters"] = [replace(" ", ""), strip_at, replace("@", ":")]
        kwargs["validators"] = [self._validate]
        super().__init__(*args, **kwargs)

    def _parse_data(self, data):
        url = urlparse(data)
        nick = url.path.lstrip("/")
        if url.netloc:
            nick = f"{nick}:{url.netloc}"
        scheme = url.scheme or "irc"
        return (scheme, nick)

    def _serialize_data(self, scheme, value):
        nick, sep_, server = value.partition(":")
        return urlunparse((scheme, server.strip(), f"/{nick.strip()}", "", "", ""))

    @staticmethod
    def _validate(form, field):
        scheme = field.subfields[0].data
        value = field.subfields[1].data
        if not value:
            return
        nick, sep_, server = value.partition(":")
        if not NICK_RE[scheme].match(nick):
            raise ValidationError(_("This does not look like a valid nickname."))
        if server and not SERVER_RE.match(server):
            raise ValidationError(_("This does not look like a valid server name."))


class UserSettingsProfileForm(BaseForm):
    firstname = StringField(
        _('First Name'),
        validators=[DataRequired(message=_('First name must not be empty'))],
    )

    lastname = StringField(
        _('Last Name'),
        validators=[DataRequired(message=_('Last name must not be empty'))],
    )

    locale = SelectField(
        _('Locale'),
        choices=[(locale, locale) for locale in LOCALES],
        validators=[
            DataRequired(message=_('Locale must not be empty')),
            AnyOf(LOCALES, message=_('Locale must be a valid locale short-code')),
        ],
    )

    ircnick = NonEmptyFieldList(
        ProtocolAndNickField(validators=[Optional()]),
        label=_('Chat Nicknames'),
    )

    timezone = SelectField(
        _('Timezone'),
        choices=[(t, t) for t in TIMEZONES],
        validators=[
            DataRequired(message=_('Timezone must not be empty')),
            AnyOf(TIMEZONES, message=_('Timezone must be a valid timezone')),
        ],
    )

    github = StringField(
        _('GitHub Username'), validators=[Optional()], filters=[strip_at]
    )

    gitlab = StringField(
        _('GitLab Username'), validators=[Optional()], filters=[strip_at]
    )

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

    pronouns = CSVListField(_('Pronouns'), validators=[Optional()])


class UserSettingsEmailForm(BaseForm):
    mail = EmailField(
        _('E-mail Address'),
        validators=[
            DataRequired(message=_('Email must not be empty')),
            Email(message=_('Email must be valid')),
        ],
    )

    rhbz_mail = EmailField(_('Red Hat Bugzilla Email'), validators=[Optional()])


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
    description = HiddenField(
        "description",
        validators=[Optional()],
    )
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


class UserSettingsOTPNameChange(BaseForm):
    token = HiddenField(
        'token', validators=[DataRequired(message=_('Token must not be empty'))]
    )
    description = StringField(
        validators=[Optional()],
    )


class UserSettingsAgreementSign(BaseForm):
    agreement = HiddenField(
        'agreement', validators=[DataRequired(message=_('Agreement must not be empty'))]
    )
