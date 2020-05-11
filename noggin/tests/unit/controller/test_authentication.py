from unittest import mock

import requests
import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import session, get_flashed_messages

from noggin import ipa_admin
from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
)


@pytest.fixture
def dummy_user_expired_password():
    ipa_admin.user_add(
        'dummy',
        'Dummy',
        'User',
        'Dummy User',
        user_password='dummy_password',
        login_shell='/bin/bash',
    )
    # Don't change the password: it will be expired
    yield
    ipa_admin.user_del('dummy')


# Logout


def test_logout_unauthed(client):
    """Test logout when not logged in"""
    result = client.get('/logout', follow_redirects=False)
    assert result.status_code == 302
    assert result.location == "http://localhost/"
    # Make sure we haven't instructed the user to login in a flash message.
    messages = get_flashed_messages()
    assert len(messages) == 0


@pytest.mark.vcr()
def test_logout(client, logged_in_dummy_user):
    """Test logout with a logged-in user"""
    result = client.get('/logout', follow_redirects=False)
    assert result.status_code == 302
    assert result.location == "http://localhost/"
    assert "noggin_session" not in session
    assert "noggin_username" not in session
    assert "noggin_ipa_server_hostname" not in session


# Login


@pytest.mark.vcr()
def test_login(client, dummy_user):
    """Test a successful Login"""
    result = client.post(
        '/',
        data={
            "login-username": "dummy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .alert-success")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Welcome, dummy!×'
    assert session.get("noggin_username") == "dummy"
    assert session.get("noggin_session") is not None


@pytest.mark.vcr()
def test_login_no_password(client, dummy_user):
    """Test not giving a password"""
    result = client.post(
        '/',
        data={"login-username": "dummy", "login-submit": "1"},
        follow_redirects=True,
    )
    assert_form_field_error(
        result,
        field_name="login-password",
        expected_message="You must provide a password",
    )
    assert "noggin_session" not in session
    assert "noggin_username" not in session


def test_login_no_username(client):
    """Test not giving a username"""
    result = client.post(
        '/',
        data={"login-password": "n:nPv{P].9}]!q$RE%w<38@", "login-submit": "1"},
        follow_redirects=True,
    )
    assert_form_field_error(
        result,
        field_name="login-username",
        expected_message="You must provide a user name",
    )
    assert "noggin_session" not in session
    assert "noggin_username" not in session


def test_login_username_case(client, dummy_user):
    """Test giving username random uppercase letter"""
    result = client.post(
        '/',
        data={
            "login-username": "duMmy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .alert-success")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Welcome, dummy!×'
    assert session.get("noggin_username") == "dummy"
    assert session.get("noggin_session") is not None


def test_login_username_created_with_case(client, dummy_user_with_case):
    """Test changing username to lowercase when created with uppercase"""
    result = client.post(
        '/',
        data={
            "login-username": "dummy",
            "login-password": "duMmy_password",
            "login-submit": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .alert-success")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Welcome, dummy!×'
    assert session.get("noggin_username") == "dummy"
    assert session.get("noggin_session") is not None


@pytest.mark.vcr()
def test_login_incorrect_password(client, dummy_user):
    """Test a incorrect password"""
    result = client.post(
        '/',
        data={
            "login-username": "dummy",
            "login-password": "an incorrect password",
            "login-submit": "1",
        },
        follow_redirects=True,
    )
    assert_form_generic_error(result, "Unauthorized: bad credentials.")
    assert "noggin_session" not in session
    assert "noggin_username" not in session


def test_login_generic_error(client):
    """Log in a user with an unhandled error"""
    with mock.patch("noggin.controller.authentication.maybe_ipa_login") as ipa_login:
        ipa_login.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/',
            data={
                "login-username": "dummy",
                "login-password": "password",
                "login-submit": "1",
            },
        )
    assert_form_generic_error(result, "Could not log in to the IPA server.")
    assert "noggin_session" not in session
    assert "noggin_username" not in session


def test_login_cant_login(client):
    """The client library could not login"""
    with mock.patch("noggin.security.ipa.Client.login", lambda *x: None):
        result = client.post(
            '/',
            data={
                "login-username": "dummy",
                "login-password": "password",
                "login-submit": "1",
            },
        )
    assert_form_generic_error(result, "Could not log in to the IPA server.")
    assert "noggin_session" not in session
    assert "noggin_username" not in session


@pytest.mark.vcr()
def test_login_expired_password(client, dummy_user_expired_password):
    """Test a successful Login with an expired password"""
    result = client.post(
        '/',
        data={
            "login-username": "dummy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
        follow_redirects=False,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/password-reset?username=dummy",
        expected_message="Password expired. Please reset it.",
        expected_category="danger",
    )
    # We are not logged in
    assert "noggin_session" not in session
    assert "noggin_username" not in session


@pytest.mark.vcr()
def test_otp_sync_no_username(client, dummy_user):
    """Test not giving a username"""
    result = client.post(
        '/otp/sync/',
        data={
            "password": "dummy_password",
            "first_code": "123456",
            "second_code": "234567",
        },
        follow_redirects=False,
    )
    assert_form_field_error(
        result, field_name="username", expected_message="You must provide a user name"
    )


@pytest.mark.vcr()
def test_otp_sync_invalid_codes(client, dummy_user_with_otp):
    """Test synchronising OTP token with madeup codes"""
    result = client.post(
        '/otp/sync/',
        data={
            "username": "dummy",
            "password": "dummy_password",
            "first_code": "123456",
            "second_code": "234567",
        },
        follow_redirects=False,
    )
    assert_form_generic_error(
        result, "The username, password or token codes are not correct."
    )


@pytest.mark.vcr()
def test_otp_sync_http_error(client, dummy_user_with_otp):
    """Test synchronising OTP token with mocked http error"""
    with mock.patch("noggin.controller.authentication.app.logger") as logger:
        with mock.patch("requests.sessions.Session.post") as method:
            method.side_effect = requests.exceptions.RequestException
            result = client.post(
                '/otp/sync/',
                data={
                    "username": "dummy",
                    "password": "dummy_password",
                    "first_code": "123456",
                    "second_code": "234567",
                },
                follow_redirects=False,
            )
    logger.error.assert_called_once()
    assert_form_generic_error(result, "Something went wrong trying to sync OTP token.")


@pytest.mark.vcr()
def test_otp_sync_rejected(client, dummy_user_with_otp):
    """Test synchronising OTP token when freeipa rejects the request"""
    with mock.patch("requests.post") as method:
        method.return_value.status_code = 200
        method.return_value.text = "Token sync rejected"
        result = client.post(
            '/otp/sync/',
            data={
                "username": "dummy",
                "password": "dummy_password",
                "first_code": "123456",
                "second_code": "234567",
            },
            follow_redirects=False,
        )
    assert_form_generic_error(
        result, "The username, password or token codes are not correct."
    )


@pytest.mark.vcr()
def test_otp_sync_success(client, dummy_user_with_otp):
    """Test synchronising OTP token"""
    with mock.patch("requests.sessions.Session.post") as method:
        method.return_value.status_code = 200
        method.return_value.text = "All good!"
        result = client.post(
            '/otp/sync/',
            data={
                "username": "dummy",
                "password": "dummy_password",
                "first_code": "123456",
                "second_code": "234567",
            },
            follow_redirects=False,
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Token successfully synchronized",
        expected_category="success",
    )
