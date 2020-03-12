from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class AddGroupMemberForm(FlaskForm):
    new_member_username = StringField(
        'New Member Username',
        validators=[DataRequired(message='New member username must not be empty')],
    )
