from flask_wtf import FlaskForm
from wtforms import RadioField


class DisableUserForm(FlaskForm):
    disable = RadioField(
        'Disable account', choices=[('no', 'no'), ('yes', 'yes')], default='no'
    )
