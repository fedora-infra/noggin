from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


class LoginUserForm(FlaskForm):
    username = StringField(
        'Username', validators=[DataRequired(message='You must provide a user name')]
    )

    password = PasswordField(
        'Password', validators=[DataRequired(message='You must provide a password')]
    )
