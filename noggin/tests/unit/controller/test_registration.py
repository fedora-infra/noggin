from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from fedora_messaging import testing as fml_testing
from flask import current_app, session
from noggin_messages import UserCreateV1

from noggin import ipa_admin
from noggin.security.ipa import maybe_ipa_login
from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
)


@pytest.fixture
def cleanup_dummy_user():
    yield
    try:
        ipa_admin.user_del('dummy')
    except python_freeipa.exceptions.NotFound:
        pass


@pytest.fixture
def post_data():
    return {
        "register-firstname": "First",
        "register-lastname": "Last",
        "register-mail": "firstlast@name.org",
        "register-username": "dummy",
        "register-password": "password",
        "register-password_confirm": "password",
        "register-submit": "1",
    }


@pytest.mark.vcr()
def test_register(client, cleanup_dummy_user):
    """Register a user"""
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            '/',
            data={
                "register-firstname": "First",
                "register-lastname": "Last",
                "register-mail": "firstlast@name.org",
                "register-username": "dummy",
                "register-password": "password",
                "register-password_confirm": "password",
                "register-submit": "1",
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
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            '/',
            data={
                "register-firstname": "First",
                "register-lastname": "Last",
                "register-mail": "firstlast@name.org",
                "register-username": "dummy",
                "register-password": "42",
                "register-password_confirm": "42",
                "register-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            'Your account has been created, but the password you chose does not comply '
            'with the policy (Constraint violation: Password is too short) and has thus '
            'been set as expired. You will be asked to change it after logging in.'
        ),
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_register_duplicate(client, dummy_user):
    """Register a user that already exists"""
    result = client.post(
        '/',
        data={
            "register-firstname": "First",
            "register-lastname": "Last",
            "register-mail": "dummy@dummy.org",
            "register-username": "dummy",
            "register-password": "password",
            "register-password_confirm": "password",
            "register-submit": "1",
        },
    )
    assert_form_field_error(
        result,
        field_name="register-username",
        expected_message='user with name "dummy" already exists',
    )


@pytest.mark.vcr()
def test_register_invalid_username(client):
    """Register a user with an invalid username"""
    result = client.post(
        '/',
        data={
            "register-firstname": "First",
            "register-lastname": "Last",
            "register-mail": "firstlast@name.org",
            "register-username": "this is invalid",
            "register-password": "password",
            "register-password_confirm": "password",
            "register-submit": "1",
        },
    )
    assert_form_field_error(
        result,
        field_name="register-username",
        expected_message='may only include letters, numbers, _, -, . and $',
    )


@pytest.mark.parametrize(
    "field_name,server_name",
    [
        ("username", "login"),
        ("firstname", "first"),
        ("lastname", "last"),
        ("password", "password"),
        ("mail", "email"),
    ],
)
def test_register_field_error(client, post_data, field_name, server_name):
    """Register a user with fields that the server errors on"""
    with mock.patch("noggin.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.ValidationError(
            message=f"invalid '{server_name}': this is invalid", code="4242"
        )
        result = client.post('/', data=post_data)
    assert_form_field_error(
        result, field_name=f"register-{field_name}", expected_message="this is invalid"
    )


def test_register_field_error_unknown(client, post_data):
    """Register a user with fields that the server errors on, but it's unknown to us"""
    with mock.patch("noggin.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.ValidationError(
            message=f"invalid 'unknown': this is invalid", code="4242"
        )
        result = client.post('/', data=post_data)
    assert_form_generic_error(
        result, expected_message="invalid 'unknown': this is invalid"
    )


def test_register_invalid_first_name(client):
    """Register a user with an invalid first name"""
    with mock.patch("noggin.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.ValidationError(
            message="invalid first name", code="4242"
        )
        result = client.post(
            '/',
            data={
                "register-firstname": "This \n is \n invalid",
                "register-lastname": "Last",
                "register-mail": "firstlast@name.org",
                "register-username": "dummy",
                "register-password": "password",
                "register-password_confirm": "password",
                "register-submit": "1",
            },
        )
    assert_form_generic_error(result, 'invalid first name')


@pytest.mark.vcr()
def test_register_invalid_email(client):
    """Register a user with an invalid email address"""
    result = client.post(
        '/',
        data={
            "register-firstname": "First",
            "register-lastname": "Last",
            "register-mail": "firstlast at name dot org",
            "register-username": "dummy",
            "register-password": "password",
            "register-password_confirm": "password",
            "register-submit": "1",
        },
    )
    assert_form_field_error(
        result, field_name="register-mail", expected_message='Email must be valid'
    )


@pytest.mark.vcr()
def test_register_empty_email(client):
    """Register a user with an empty email address"""
    result = client.post(
        '/',
        data={
            "register-firstname": "First",
            "register-lastname": "Last",
            "register-username": "dummy",
            "register-password": "password",
            "register-password_confirm": "password",
            "register-submit": "1",
        },
    )
    assert_form_field_error(
        result, field_name="register-mail", expected_message='Email must not be empty'
    )


def test_register_generic_error(client):
    """Register a user with an unhandled error"""
    with mock.patch("noggin.controller.registration.ipa_admin") as ipa_admin:
        ipa_admin.user_add.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/',
            data={
                "register-firstname": "First",
                "register-lastname": "Last",
                "register-mail": "firstlast@name.org",
                "register-username": "dummy",
                "register-password": "password",
                "register-password_confirm": "password",
                "register-submit": "1",
            },
        )
    assert_form_generic_error(
        result, 'An error occurred while creating the account, please try again.'
    )


@pytest.mark.vcr()
def test_register_generic_pwchange_error(client, cleanup_dummy_user):
    """Change user's password with an unhandled error"""
    ipa_client = mock.Mock()
    ipa_client.change_password.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    with mock.patch(
        "noggin.controller.registration.untouched_ipa_client", lambda a: ipa_client
    ):
        with fml_testing.mock_sends(
            UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
        ):
            result = client.post(
                '/',
                data={
                    "register-firstname": "First",
                    "register-lastname": "Last",
                    "register-mail": "firstlast@name.org",
                    "register-username": "dummy",
                    "register-password": "password",
                    "register-password_confirm": "password",
                    "register-submit": "1",
                },
            )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            'Your account has been created, but an error occurred while setting your '
            'password (something went wrong). You may need to change it after logging in.'
        ),
        expected_category="warning",
    )


def test_register_get(client):
    """Display the registration page"""
    result = client.get('/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    forms = page.select("form[action='/']")
    assert len(forms) == 1


@pytest.mark.vcr()
def test_register_default_values(client, cleanup_dummy_user):
    """Verify that the default attributes are added to the user"""
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            '/',
            data={
                "register-firstname": "First",
                "register-lastname": "Last",
                "register-mail": "firstlast@name.org",
                "register-username": "dummy",
                "register-password": "password",
                "register-password_confirm": "password",
                "register-submit": "1",
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
