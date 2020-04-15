from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import HiddenField
from wtforms.validators import DataRequired


class RemoveGroupMemberForm(FlaskForm):
    username = HiddenField(
        _('Username'),
        validators=[DataRequired(message=_('Username must not be empty'))],
    )
