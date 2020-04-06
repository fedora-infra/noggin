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

    password_confirm = PasswordField('Confirm New Password')

    otp = StringField(
        'OTP Token', description="Enter your OTP token if you have enrolled one"
    )


class PasswordResetForm(NewPasswordForm):

    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired(message='Current password must not be empty')],
        description="Just the password, don't add the OTP token if you have one",
    )


class ForgottenPasswordForm(FlaskForm):

    username = StringField(
        'Username',
        validators=[DataRequired(message='User name must not be empty')],
        description="Enter your username to reset your password",
    )
