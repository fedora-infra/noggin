from unittest import mock

import pytest
from flask import current_app, g, session, get_flashed_messages
from werkzeug.exceptions import NotFound, InternalServerError

from noggin.security.ipa import maybe_ipa_login
from noggin.utility import (
    user_or_404,
    group_or_404,
    with_ipa,
    FormError,
    handle_form_errors,
    require_self,
)
from noggin.form.login_user import LoginUserForm


@pytest.mark.vcr()
def test_user_or_404(client, logged_in_dummy_user):
    """Test the user_or_404 method"""
    result = user_or_404(logged_in_dummy_user, "dummy")
    assert result is not None
    assert result["uid"] == ["dummy"]


@pytest.mark.vcr()
def test_user_or_404_unknown(client, logged_in_dummy_user):
    """Test the user_or_404 method on an unknown user"""
    with pytest.raises(NotFound):
        user_or_404(logged_in_dummy_user, "unknown")


@pytest.mark.vcr()
def test_group_or_404(client, logged_in_dummy_user, dummy_group):
    """Test the group_or_404 method"""
    result = group_or_404(logged_in_dummy_user, "dummy-group")
    assert result is not None
    assert result["cn"] == ["dummy-group"]


@pytest.mark.vcr()
def test_group_or_404_unknown(client, logged_in_dummy_user):
    """Test the group_or_404 method on an unknown group"""
    with pytest.raises(NotFound):
        group_or_404(logged_in_dummy_user, "unknown")


@pytest.mark.vcr()
def test_with_ipa(client, dummy_user):
    """Test the with_ipa decorator"""
    view = mock.Mock()
    with current_app.test_request_context('/'):
        ipa = maybe_ipa_login(current_app, session, "dummy", "dummy_password")
        wrapped = with_ipa(current_app, session)(view)
        wrapped("arg")
        view.assert_called_once()
        assert "ipa" in view.call_args_list[0][1]
        assert isinstance(view.call_args_list[0][1]["ipa"], ipa.__class__)
        assert "arg" in view.call_args_list[0][0]
        assert "ipa" in g
        assert isinstance(g.ipa, ipa.__class__)
        assert "current_user" in g
        assert g.current_user.username == "dummy"


@pytest.mark.vcr()
def test_with_ipa_anonymous(client):
    """Test the with_ipa decorator on anonymous users"""
    view = mock.Mock()
    with current_app.test_request_context('/'):
        wrapped = with_ipa(current_app, session)(view)
        response = wrapped("arg")
        assert response.status_code == 302
        assert response.location == "/"
        view.assert_not_called()
        assert "ipa" not in g
        assert "current_user" not in g
        messages = get_flashed_messages(with_categories=True)
        assert len(messages) == 1
        category, message = messages[0]
        assert message == "Please log in to continue."
        assert category == "warning"


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
        error = FormError("non_form_errors", "error message")
        error.populate_form(form)
    assert form.errors == {"non_form_errors": ["error message"]}


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
        FormError("non_form_errors", "error message 1").populate_form(form)
        FormError("non_form_errors", "error message 2").populate_form(form)
    assert form.errors["non_form_errors"] == ["error message 1", "error message 2"]


def test_handle_form_errors(client):
    with current_app.test_request_context('/'):
        form = LoginUserForm()
        error = FormError("username", "error_message")
        with mock.patch.object(error, "populate_form") as populate_form:
            with handle_form_errors(form):
                raise error
    populate_form.assert_called_once_with(form)


def test_require_self_wrong_route(client):
    view = mock.Mock()
    with current_app.test_request_context('/password-reset'):
        with pytest.raises(InternalServerError):
            require_self(view)()
