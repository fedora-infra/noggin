from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField
from wtforms.validators import DataRequired

class AddGroupMemberForm(FlaskForm):
    groupname = HiddenField(
        'Group Name',
        validators=[
            DataRequired(message='Group name must not be empty'),
        ])

    new_member_username = StringField(
        'New Member Username',
        validators=[
            DataRequired(message='New member username must not be empty'),
        ])
