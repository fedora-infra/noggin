from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Optional


class SyncTokenForm(FlaskForm):
    username = StringField(
        'Username', validators=[DataRequired(message='You must provide a user name')]
    )

    password = PasswordField(
        'Password', validators=[DataRequired(message='You must provide a password')]
    )

    first_code = StringField(
        'First OTP', validators=[DataRequired(message='You must provide a first code')]
    )

    second_code = StringField(
        'Second OTP',
        validators=[DataRequired(message='You must provide a second code')],
    )

    token = StringField('Token ID', validators=[Optional()])
