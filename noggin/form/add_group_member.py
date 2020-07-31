from flask_babel import lazy_gettext as _
from wtforms import StringField
from wtforms.validators import DataRequired

from .base import BaseForm


class AddGroupMemberForm(BaseForm):
    new_member_username = StringField(
        'New Member Username',
        validators=[DataRequired(message=_('New member username must not be empty'))],
    )
