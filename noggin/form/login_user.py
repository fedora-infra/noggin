from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from .base import ModestForm, SubmitButtonField


class LoginUserForm(ModestForm):
    username = StringField(
        'Username', validators=[DataRequired(message='You must provide a user name')]
    )

    password = PasswordField(
        'Password', validators=[DataRequired(message='You must provide a password')]
    )

    submit = SubmitButtonField('Log In')
