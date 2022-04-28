from collections import namedtuple

import pytest
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

from noggin.form.base import ButtonWidget, CSVListField, ModestForm, SubmitButtonField


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


def test_modestform(client):
    class TestForm(ModestForm):
        text = StringField()
        submit = SubmitButtonField()

    with current_app.test_request_context('/', method="POST", data={"submit": "1"}):
        form = TestForm()
        assert form.is_submitted()


def test_modestform_button_not_clicked(client):
    class TestForm(ModestForm):
        text = StringField()
        submit = SubmitButtonField()

    with current_app.test_request_context(
        '/', method="POST", data={"text": "dummy value"}
    ):
        form = TestForm()
        assert not form.is_submitted()


def test_modestform_no_submit_button(client):
    class TestForm(ModestForm):
        text = StringField()

    with current_app.test_request_context(
        '/', method="POST", data={"text": "dummy value"}
    ):
        form = TestForm()
        assert form.is_submitted()


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
