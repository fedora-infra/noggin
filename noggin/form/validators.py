from flask import current_app
from flask_babel import lazy_gettext as _
from wtforms.validators import Email as WTFormsEmailValidator
from wtforms.validators import Length, StopValidation, ValidationError


class Email(WTFormsEmailValidator):
    """Extend the WTForms email validator, adding the ability to blocklist
    email addresses
    """

    def __call__(self, form, field):
        super().__call__(form, field)
        blocklist = current_app.config["MAIL_DOMAIN_BLOCKLIST"]
        domain = field.data.split("@")[1]
        if domain in blocklist:
            raise ValidationError(_('Email addresses from that domain are not allowed'))


class PasswordLength:
    """Set defaults from the Flask config"""

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        validator = Length(
            min=current_app.config["PASSWORD_POLICY"].get("min", -1),
            max=current_app.config["PASSWORD_POLICY"].get("max", -1),
            message=self.message,
        )
        validator(form, field)


def no_mixed_case(form, field):
    if field.data != field.data.lower():
        raise ValidationError(_("Mixed case is not allowed, try lower case."))


def validator_proxy(factory):
    """Proxy the validator through a factory to allow access to current_app."""

    def _validate(form, field):
        validator = factory()
        return validator(form, field)

    return _validate


class StopOnError:
    def __init__(self, validator):
        self.validator = validator

    def __call__(self, form, field):
        try:
            self.validator(form, field)
        except ValidationError as e:
            raise StopValidation(str(e))
