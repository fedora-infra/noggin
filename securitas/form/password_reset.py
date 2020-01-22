from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, EqualTo


class PasswordResetForm(FlaskForm):
    username = StringField(
      'Username',
      validators=[DataRequired(message='User name must not be empty')]
    )

    current_password = PasswordField(
      'Current Password',
      validators=[DataRequired(message='Current password must not be empty')]
    )

    password = PasswordField(
      'New Password',
      validators=[
          DataRequired(message='Password must not be empty'),
          EqualTo('password_confirm', message='Passwords must match'),
      ]
    )

    password_confirm = PasswordField('Confirm Password')
