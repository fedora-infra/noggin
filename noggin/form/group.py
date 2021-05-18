from flask_babel import lazy_gettext as _
from wtforms import HiddenField, StringField
from wtforms.validators import DataRequired

from .base import BaseForm


class AddGroupMemberForm(BaseForm):
    new_member_username = StringField(
        'New Member Username',
        validators=[DataRequired(message=_('New member username must not be empty'))],
    )


class RemoveGroupMemberForm(BaseForm):
    username = HiddenField(
        _('Username'),
        validators=[DataRequired(message=_('Username must not be empty'))],
    )
