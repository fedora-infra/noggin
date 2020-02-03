from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import get_flashed_messages


def test_password_reset(client):
    """Test the password reset page"""

    # check that when unauthed, we redirect back to /
    result = client.get('/password-reset')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Password Reset - The Fedora Project'


def test_non_matching_passwords(client):
    """Verify that passwords that dont match are caught"""
    result = client.post(
        '/password-reset',
        data={
            "username": "jbloggs",
            "current_password": "sdsds",
            "password": "password1",
            "password_confirm": "password2",
        },
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'is-invalid' in password_input['class']
    invalidfeedback = password_input.find_next('div', class_='invalid-feedback')
    assert invalidfeedback.get_text(strip=True) == "Passwords must match"


@pytest.mark.vcr()
def test_password(client, dummy_user):
    """Verify that current password must be correct"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='current_password']")[0]
    assert 'is-invalid' in password_input['class']
    invalidfeedback = password_input.find_next('div', class_='invalid-feedback')
    assert (
        invalidfeedback.get_text(strip=True)
        == "The old password or username is not correct"
    )


@pytest.mark.vcr()
def test_time_sensitive_password_policy(client, dummy_user):
    """Verify that new password policies are upheld"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "dummy_password",
            "password": "somesupersecretpassword",
            "password_confirm": "somesupersecretpassword",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'is-invalid' in password_input['class']
    # the dummy user is created and has its password immediately changed,
    # so this next attempt should failt with a constraint error.
    invalidfeedback = password_input.find_next('div', class_='invalid-feedback')
    assert (
        invalidfeedback.get_text(strip=True)
        == "Constraint violation: Too soon to change password"
    )


@pytest.mark.vcr()
def test_short_password(client, dummy_user, no_password_min_time):
    """Verify that new password policies are upheld"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "dummy_password",
            "password": "1",
            "password_confirm": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'is-invalid' in password_input['class']
    invalidfeedback = password_input.find_next('div', class_='invalid-feedback')
    assert (
        invalidfeedback.get_text(strip=True)
        == "Constraint violation: Password is too short"
    )


def test_reset_generic_error(client):
    """Reset password with an unhandled error"""
    client_mock = mock.Mock()
    with mock.patch(
        "securitas.controller.password.untouched_ipa_client"
    ) as untouched_ipa_client:
        untouched_ipa_client.return_value = client_mock
        client_mock.change_password.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/password-reset',
            data={
                "username": "dummy",
                "current_password": "dummy_password",
                "password": "password",
                "password_confirm": "password",
            },
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    submit_button = page.select("button[type='submit']")[0]
    form_errors = submit_button.find_previous("div", id="formerrors")
    assert form_errors is not None
    form_error = form_errors.find("div", class_="text-danger")
    assert form_error is not None
    assert form_error.get_text(strip=True) == 'Could not change password.'


@pytest.mark.vcr()
def test_password_changes(client, dummy_user, no_password_min_time):
    """Verify that password changes"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "dummy_password",
            "password": "secretpw",
            "password_confirm": "secretpw",
        },
    )
    assert result.status_code == 302
    assert result.location == f"http://localhost/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert (
        message
        == "Your password has been changed, please try to log in with the new one now."
    )
    assert category == "success"
