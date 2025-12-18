from flask_wtf import FlaskForm
from wtforms import Field, SubmitField


class BaseForm(FlaskForm):
    """Add an invisible field to hold form-wide errors."""

    non_field_errors = Field()


class ModestForm(BaseForm):
    """A form that can handle not being the only form on the page."""

    def _get_submit_field(self):
        for field in self:
            if isinstance(field, SubmitField):
                return field

    def is_submitted(self):
        submit_field = self._get_submit_field()
        submit_data = submit_field.data if submit_field is not None else True
        return super().is_submitted() and submit_data


def strip(value):
    return value.strip() if value else value


def strip_at(value):
    return value.lstrip("@") if value else value


def lower(value):
    return value.lower() if value else value


def replace(target, replacement):
    def _replace(value):
        return value.replace(target, replacement) if value else value

    return _replace
