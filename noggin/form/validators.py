from flask_babel import lazy_gettext as _
from wtforms.validators import ValidationError
from wtforms.validators import Email as WTFormsEmailValidator


class Email(WTFormsEmailValidator):
    """ Extend the WTForms email validator, adding the ability to blocklist
        email addresses
    """

    def __init__(self, blocklist=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocklist = blocklist

    def __call__(self, form, field):
        super().__call__(form, field)
        domain = field.data.split("@")[1]
        if domain in self.blocklist:
            raise ValidationError(_('Email addresses from that domain are not allowed'))
