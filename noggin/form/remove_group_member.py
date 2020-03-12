from flask_wtf import FlaskForm
from wtforms import HiddenField
from wtforms.validators import DataRequired


class RemoveGroupMemberForm(FlaskForm):
    username = HiddenField(
        'Username', validators=[DataRequired(message='Username must not be empty')]
    )
