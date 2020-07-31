from unittest import mock

from flask import current_app

from noggin.form.login_user import LoginUserForm
from noggin.utility.forms import FormError, handle_form_errors


def test_formerror(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm(data={"username": "dummy", "password": "passwd"})
        form.validate()
        error = FormError("username", "error message")
        error.populate_form(form)
    assert form.errors == {"username": ["error message"]}


def test_formerror_unknown_field(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm(data={"username": "dummy", "password": "passwd"})
        form.validate()
        error = FormError("non_field_errors", "error message")
        error.populate_form(form)
    assert form.errors == {"non_field_errors": ["error message"]}


def test_formerror_existing_field(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm()
        form.validate()
        error = FormError("username", "error message")
        error.populate_form(form)
        assert form.errors["username"] == [
            "You must provide a user name",
            "error message",
        ]


def test_formerror_unknown_field_append(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm()
        form.validate()
        FormError("non_field_errors", "error message 1").populate_form(form)
        FormError("non_field_errors", "error message 2").populate_form(form)
    assert form.errors["non_field_errors"] == ["error message 1", "error message 2"]


def test_handle_form_errors(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm()
        error = FormError("username", "error_message")
        with mock.patch.object(error, "populate_form") as populate_form:
            with handle_form_errors(form):
                raise error
    populate_form.assert_called_once_with(form)
