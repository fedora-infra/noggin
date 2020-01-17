from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import session, get_flashed_messages


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
    assert "securitas_session" not in session
    assert "securitas_username" not in session
    assert "securitas_ipa_server_hostname" not in session


@pytest.mark.vcr()
def test_login(client):
    """Test a successful Login"""
    result = client.post(
        '/login',
        data={"username": "dudemcpants", "password": "n:nPv{P].9}]!q$RE%w<38@"},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .green")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Welcome, dudemcpants!'
    assert session.get("securitas_username") == "dudemcpants"
    assert session.get("securitas_session") is not None


def test_login_no_password(client):
    """Test not giving a password"""
    result = client.post(
        '/login', data={"username": "dudemcpants"}, follow_redirects=True
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'invalid' in password_input['class']
    helper_text = password_input.find_next("span", class_="helper-text")
    assert helper_text["data-error"] == "You must provide a password"
    assert "securitas_session" not in session
    assert "securitas_username" not in session


def test_login_no_username(client):
    """Test not giving a password"""
    result = client.post(
        '/login', data={"password": "n:nPv{P].9}]!q$RE%w<38@"}, follow_redirects=True
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    username_input = page.select("input[name='username']")[0]
    assert 'invalid' in username_input['class']
    helper_text = username_input.find_next("span", class_="helper-text")
    assert helper_text["data-error"] == "You must provide a user name"
    assert "securitas_session" not in session
    assert "securitas_username" not in session


@pytest.mark.vcr()
def test_login_incorrect_password(client):
    """Test a incorrect password"""
    result = client.post(
        '/login',
        data={"username": "dudemcpants", "password": "an incorrect password"},
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    submit_button = page.select("button[type='submit']")[0]
    error_message = submit_button.find_next("p")
    assert "red-text" in error_message["class"]
    assert error_message.get_text(strip=True) == 'Unauthorized: bad credentials.'
    assert "securitas_session" not in session
    assert "securitas_username" not in session


def test_login_generic_error(client):
    """Log in a user with an unhandled error"""
    with mock.patch("securitas.controller.authentication.maybe_ipa_login") as ipa_login:
        ipa_login.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/login', data={"username": "dummy", "password": "password"}
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    submit_button = page.select("button[type='submit']")[0]
    error_message = submit_button.find_next("p")
    assert "red-text" in error_message["class"]
    assert error_message.string == 'Could not log in to the IPA server.'
    assert "securitas_session" not in session
    assert "securitas_username" not in session


def test_login_cant_login(client):
    """The client library could not login"""
    with mock.patch("securitas.security.ipa.Client.login", lambda *x: None):
        result = client.post(
            '/login', data={"username": "dummy", "password": "password"}
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    submit_button = page.select("button[type='submit']")[0]
    error_message = submit_button.find_next("p")
    assert "red-text" in error_message["class"]
    assert error_message.string == 'Could not log in to the IPA server.'
    assert "securitas_session" not in session
    assert "securitas_username" not in session
