from collections import namedtuple

import pytest
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import StopValidation

from noggin.form.fields import (
    AltchaField,
    ButtonWidget,
    CSVListField,
)


def test_buttonwidget(client):
    class TestForm(FlaskForm):
        submit = SubmitField()
        text = StringField()

    form = TestForm()
    widget = ButtonWidget()
    kwargs = {"class": "testclass", "testattr": "testvalue"}
    output = widget(form.submit, **kwargs)
    assert output == (
        '<button class="btn testclass" id="submit" name="submit" '
        'testattr="testvalue" type="button">Submit</button>'
    )


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["one,two,three"], ["one", "two", "three"]),
        ([" "], []),
        ([" , , , "], []),
        ([""], []),
        ([], []),
    ],
)
def test_csvlistfield(client, test_input, expected):
    class DummyForm(FlaskForm):
        csvfield = CSVListField('csv field')

    form = DummyForm()

    form.csvfield.process_formdata(test_input)
    assert form.csvfield.data == expected


@pytest.mark.parametrize(
    "data,expected",
    [(["one", "two", "three"], "one,two,three"), ([""], ""), ([], "")],
)
def test_csvlistfield_read(client, data, expected):
    class DummyForm(FlaskForm):
        csvfield = CSVListField('csv field')

    Obj = namedtuple("Obj", ["csvfield"])

    form = DummyForm(obj=Obj(csvfield=data))
    assert form.csvfield._value() == expected


def test_altcha_field_no_data(request_context, mocker):
    mocker.patch(
        "noggin.form.fields.verify_solution", return_value=(False, "dummy error")
    )

    class DummyForm(FlaskForm):
        altcha = AltchaField()

    Data = namedtuple("Data", ["altcha"])
    form = DummyForm(obj=Data(altcha=""))
    assert form.validate() is False
    assert form.errors == {'altcha': ['CAPTCHA payload missing']}


def test_altcha_field_stopped_validation(request_context, mocker):
    mocker.patch(
        "noggin.form.fields.verify_solution", return_value=(False, "dummy error")
    )

    def stopping_validator(form, field):
        raise StopValidation()

    class DummyForm(FlaskForm):
        altcha = AltchaField(validators=[stopping_validator])

    form = DummyForm()
    form.validate()
