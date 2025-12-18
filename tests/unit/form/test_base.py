from flask import current_app
from wtforms import StringField

from noggin.form.base import ModestForm
from noggin.form.fields import SubmitButtonField


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
