from flask_wtf import FlaskForm
from markupsafe import escape, Markup
from wtforms import Field, SubmitField
from wtforms.fields import FieldList, SelectField, StringField
from wtforms.utils import unset_value
from wtforms.widgets import html_params, TextInput


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


def strip_at(value):
    return value.lstrip("@") if value else value


def lower(value):
    return value.lower() if value else value


def replace(target, replacement):
    def _replace(value):
        return value.replace(target, replacement) if value else value

    return _replace


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


class TypeAndStringWidget(TextInput):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        errors = [str(e) for e in field.errors or []]
        if errors:
            errors.insert(0, '<div class="invalid-feedback d-block">')
            errors.append('</div>')
        html = [
            '<div class="input-group">',
            '<div class="input-group-prepend">',
            field.subfields[0](class_="custom-select"),
            '</div>',
            field.subfields[1](**kwargs),
            '<div class="input-group-append">',
            '<button class="btn btn-outline-secondary form-control" '
            'data-action="clear" type="button">',
            '<i class="fa fa-fw fa-times"></i>',
            '</button>',
            '</div>',
            '</div>',
            " ".join(errors),
        ]
        return Markup(''.join(html))


class TypeAndStringField(Field):
    widget = TypeAndStringWidget()

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop("choices", None)
        super().__init__(*args, **kwargs)
        self._prefix = kwargs.get('_prefix', '')
        self.subfields = []
        self._add_field("type", SelectField(choices=choices))
        self._add_field(
            "value",
            StringField(
                filters=kwargs.get("filters"), validators=kwargs.get("validators")
            ),
        )

    def _parse_data(self, data):
        raise NotImplementedError  # pragma: no cover

    def _serialize_data(self, scheme, value):
        raise NotImplementedError  # pragma: no cover

    def _add_field(self, name, unbound_field):
        self.subfields.append(
            unbound_field.bind(
                form=None,
                name=f"{self.short_name}-{name}",
                prefix=self._prefix,
                id=f"{self.id}-{name}",
                _meta=self.meta,
                translations=self._translations,
            )
        )

    def process(self, formdata, data=unset_value):
        if data:
            data = self._parse_data(data)
        else:
            data = (unset_value, unset_value)
        for field, field_data in zip(self.subfields, data):
            field.process(formdata, field_data)

    @property
    def data(self):
        scheme = self.subfields[0].data
        value = self.subfields[1].data
        if not value:
            return ""
        return self._serialize_data(scheme, value)


class NonEmptyFieldList(FieldList):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = "FieldList"

    @property
    def data(self):
        return [f.data.strip() for f in self.entries if f.data and f.data.strip()]
