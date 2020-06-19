from flask_babel import lazy_gettext as _
from wtforms import HiddenField
from wtforms.validators import DataRequired

from .base import BaseForm


class RemoveGroupMemberForm(BaseForm):
    username = HiddenField(
        _('Username'),
        validators=[DataRequired(message=_('Username must not be empty'))],
    )
