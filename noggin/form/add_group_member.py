from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _


class AddGroupMemberForm(FlaskForm):
    new_member_username = StringField(
        'New Member Username',
        validators=[DataRequired(message=_('New member username must not be empty'))],
    )
