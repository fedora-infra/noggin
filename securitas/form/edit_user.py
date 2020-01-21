from flask_wtf import FlaskForm
from wtforms import FieldList, StringField
from wtforms.validators import AnyOf, DataRequired, Email, Optional

from securitas.utility.locales import LOCALES
from securitas.utility.timezones import TIMEZONES


class EditUserForm(FlaskForm):
    firstname = StringField(
        'First Name', validators=[DataRequired(message='First name must not be empty')]
    )

    lastname = StringField(
        'Last Name', validators=[DataRequired(message='Last name must not be empty')]
    )

    mail = StringField(
        'E-mail Address',
        validators=[
            DataRequired(message='Email must not be empty'),
            Email(message='Email must be valid'),
        ],
    )

    locale = StringField(
        'Locale',
        validators=[
            DataRequired(message='Locale must not be empty'),
            AnyOf(LOCALES, message='Locale must be a valid locale short-code'),
        ],
    )

    ircnick = StringField('IRC Nickname', validators=[Optional()])

    gpgkeys = FieldList(StringField('GPG Keys', validators=[Optional()]))

    timezone = StringField(
        'Timezone',
        validators=[
            DataRequired(message='Timezone must not be empty'),
            AnyOf(TIMEZONES, message='Timezone must be a valid timezone'),
        ],
    )

    github = StringField('GitHub Username', validators=[Optional()])

    gitlab = StringField('GitLab Username', validators=[Optional()])

    rhbz_mail = StringField(
        'E-mail Address used in Red Hat Bugzilla', validators=[Optional()]
    )
