from flask_wtf import FlaskForm
from wtforms import HiddenField
from wtforms.validators import DataRequired


class RemoveGroupMemberForm(FlaskForm):
    groupname = HiddenField(
        'Group Name', validators=[DataRequired(message='Group name must not be empty'),]
    )

    username = HiddenField(
        'Username', validators=[DataRequired(message='Username must not be empty'),]
    )
