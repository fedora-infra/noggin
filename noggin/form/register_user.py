from wtforms import StringField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo, Email

from .base import ModestForm, SubmitButtonField, strip


class RegisterUserForm(ModestForm):
    firstname = StringField(
        'First Name',
        validators=[DataRequired(message='First name must not be empty')],
        filters=[strip],
    )

    lastname = StringField(
        'Last Name',
        validators=[DataRequired(message='Last name must not be empty')],
        filters=[strip],
    )

    username = StringField(
        'Username',
        validators=[DataRequired(message='User name must not be empty')],
        filters=[strip],
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password must not be empty'),
            EqualTo('password_confirm', message='Passwords must match'),
        ],
        filters=[strip],
        description="Please choose a strong password",
    )

    password_confirm = PasswordField('Confirm Password', filters=[strip])

    mail = EmailField(
        'E-mail Address',
        validators=[
            DataRequired(message='Email must not be empty'),
            Email(message='Email must be valid'),
        ],
        filters=[strip],
    )

    submit = SubmitButtonField("Register")
