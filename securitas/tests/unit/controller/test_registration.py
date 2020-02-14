from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import current_app, session, get_flashed_messages
from securitas import ipa_admin
from securitas.security.ipa import maybe_ipa_login


@pytest.fixture
def cleanup_dummy_user():
    yield
    ipa_admin.user_del('dummy')


@pytest.mark.vcr()
def test_register(client, cleanup_dummy_user):
    """Register a user"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "dummy",
            "password": "password",
            "password_confirm": "password",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .alert-success")
    assert len(messages) == 1
    assert (
        messages[0].get_text(strip=True)
        == 'Congratulations, you now have an account! Go ahead and sign in to proceed.×'
    )


@pytest.mark.vcr()
def test_register_short_password(client, cleanup_dummy_user):
    """Register a user with too short a password"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "dummy",
            "password": "42",
            "password_confirm": "42",
        },
    )
    assert result.status_code == 302
    assert result.location == f"http://localhost/login"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == (
        'Your account has been created, but the password you chose does not comply '
        'with the policy (Constraint violation: Password is too short) and has thus '
        'been set as expired. You will be asked to change it after logging in.'
    )
    assert category == "warning"


@pytest.mark.vcr()
def test_register_duplicate(client, dummy_user):
    """Register a user that already exists"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "dummy",
            "password": "password",
            "password_confirm": "password",
        },
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    username_input = page.select("input[name='username']")[0]
    assert 'is-invalid' in username_input['class']
    invalidfeedback = username_input.find_next('div', class_='invalid-feedback')
    assert (
        invalidfeedback.get_text(strip=True) == 'user with name "dummy" already exists'
    )


@pytest.mark.vcr()
def test_register_invalid_username(client):
    """Register a user with an invalid username"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "this is invalid",
            "password": "password",
            "password_confirm": "password",
        },
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    username_input = page.select("input[name='username']")[0]
    assert 'is-invalid' in username_input['class']
    invalidfeedback = username_input.find_next('div', class_='invalid-feedback')
    assert (
        invalidfeedback.get_text(strip=True)
        == 'may only include letters, numbers, _, -, . and $'
    )


def test_register_invalid_first_name(client):
    """Register a user with an unhandled invalid value"""
    with mock.patch("securitas.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.ValidationError(
            message="invalid first name", code="4242"
        )
        result = client.post(
            '/register',
            data={
                "firstname": "This \n is \n invalid",
                "lastname": "Last",
                "username": "dummy",
                "password": "password",
                "password_confirm": "password",
            },
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    error_message = page.select("#formerrors .text-danger")[0]
    assert error_message.string == 'invalid first name'


def test_register_generic_error(client):
    """Register a user with an unhandled error"""
    with mock.patch("securitas.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/register',
            data={
                "firstname": "First",
                "lastname": "Last",
                "username": "dummy",
                "password": "password",
                "password_confirm": "password",
            },
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    error_message = page.select("#formerrors .text-danger")[0]
    assert (
        error_message.string
        == 'An error occurred while creating the account, please try again.'
    )


@pytest.mark.vcr()
def test_register_generic_pwchange_error(client, cleanup_dummy_user):
    """Change user's password with an unhandled error"""
    ipa_client = mock.Mock()
    ipa_client.change_password.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    with mock.patch(
        "securitas.controller.registration.untouched_ipa_client", lambda a: ipa_client
    ):
        result = client.post(
            '/register',
            data={
                "firstname": "First",
                "lastname": "Last",
                "username": "dummy",
                "password": "password",
                "password_confirm": "password",
            },
        )
    assert result.status_code == 302
    assert result.location == f"http://localhost/login"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == (
        'Your account has been created, but an error occurred while setting your '
        'password (something went wrong). You may need to change it after logging in.'
    )
    assert category == "warning"


def test_register_get(client):
    """Display the registration page"""
    result = client.get('/register')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    forms = page.select("form[action='/register']")
    assert len(forms) == 1


@pytest.mark.vcr()
def test_register_default_values(client, cleanup_dummy_user):
    """Verify that the default attributes are added to the user"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "dummy",
            "password": "password",
            "password_confirm": "password",
        },
    )
    assert result.status_code == 302
    ipa = maybe_ipa_login(current_app, session, "dummy", "password")
    user = ipa.user_show("dummy")
    # Creation time
    assert "fascreationtime" in user
    assert user["fascreationtime"][0]
    # Locale
    assert "faslocale" in user
    assert user["faslocale"][0] == current_app.config["USER_DEFAULTS"]["user_locale"]
    # Timezone
    assert "fastimezone" in user
    assert (
        user["fastimezone"][0] == current_app.config["USER_DEFAULTS"]["user_timezone"]
    )
