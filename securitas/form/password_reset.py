from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo


class NewPasswordForm(FlaskForm):

    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='Password must not be empty'),
            EqualTo('password_confirm', message='Passwords must match'),
        ],
    )

    password_confirm = PasswordField('Confirm Password')


class PasswordResetForm(NewPasswordForm):

    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired(message='Current password must not be empty')],
    )


class ForgottenPasswordForm(FlaskForm):

    username = StringField(
        'Username',
        validators=[DataRequired(message='User name must not be empty')],
        description="Enter your username to reset your password",
    )
