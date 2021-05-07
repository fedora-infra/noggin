from flask_wtf import FlaskForm
from markupsafe import escape, Markup
from wtforms import Field, SubmitField
from wtforms.widgets import TextInput
from wtforms.widgets.core import html_params


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


class ButtonWidget:
    """
    Renders a button.

    The field's label is used as the text of the button instead of the
    data on the field.
    """

    button_type = "button"

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.button_type)
        kwargs["name"] = field.name
        label = kwargs.pop("label", field.label.text)
        # CSS classes
        classes = ["btn"]
        if "color" in kwargs:
            classes.append("btn-{}".format(kwargs.pop("color")))
        classes.append(kwargs.get("class"))
        kwargs["class"] = " ".join(c for c in classes if c)
        # Rendering
        return Markup(f"<button {html_params(**kwargs)}>{escape(label)}</button>")


class ButtonSubmitWidget(ButtonWidget):
    """
    Renders a submit button as a button tag.
    """

    button_type = "submit"

    def __call__(self, field, **kwargs):
        kwargs.setdefault('value', '1')
        return super().__call__(field, **kwargs)


class SubmitButtonField(SubmitField):
    widget = ButtonSubmitWidget()


def strip(value):
    return value.strip() if value else value


def lower(value):
    return value.lower() if value else value


class CSVListField(Field):
    widget = TextInput()

    def _value(self):
        if self.data:
            return ','.join(self.data)
        else:
            return ''

    def process_formdata(self, values):
        if values:
            self.data = [x.strip() for x in values[0].split(',') if x.strip()]
        else:
            self.data = []
