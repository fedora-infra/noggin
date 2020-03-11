import datetime
import re
from unittest import mock

import jwt
import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import current_app

from securitas import ipa_admin, mailer
from securitas.security.ipa import untouched_ipa_client
from securitas.utility.password_reset import PasswordResetLock
from securitas.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
)


@pytest.fixture
def token_for_dummy_user(dummy_user):
    last_change = ipa_admin.user_show("dummy")["krblastpwdchange"]
    return str(
        jwt.encode(
            {"username": "dummy", "last_change": last_change},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        ),
        "ascii",
    )


@pytest.fixture
def patched_lock():
    with mock.patch.multiple(
        PasswordResetLock,
        valid_until=mock.DEFAULT,
        delete=mock.DEFAULT,
        store=mock.DEFAULT,
    ) as patches:
        patches["valid_until"].return_value = None
        yield patches


@pytest.fixture
def patched_lock_active(patched_lock):
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=2)
    patched_lock["valid_until"].return_value = expiry
    yield patched_lock


def test_ask_get(client):
    result = client.get('/forgot-password/ask')
    assert result.status_code == 200


@pytest.mark.vcr()
def test_ask_post(client, dummy_user, patched_lock):
    with mailer.record_messages() as outbox:
        result = client.post('/forgot-password/ask', data={"username": "dummy"})
    # Confirmation message
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            "An email has been sent to your address with instructions on how to reset "
            "your password"
        ),
        expected_category="success",
    )
    # Sent email
    assert len(outbox) == 1
    message = outbox[0]
    assert message.subject == "Password reset procedure"
    assert message.recipients == ["dummy@example.com"]
    # Valid token
    token_match = re.search(r"\?token=([^\s\"']+)", message.body)
    assert token_match is not None
    token = token_match.group(1)
    token_data = jwt.decode(
        token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
    )
    assert token_data.get("username") == "dummy"
    assert "last_change" in token_data
    # Lock activated
    patched_lock["store"].assert_called_once()


@pytest.mark.vcr()
def test_ask_post_non_existant_user(client):
    result = client.post('/forgot-password/ask', data={"username": "nosuchuser"})
    assert_form_field_error(
        result, field_name="username", expected_message="User nosuchuser does not exist"
    )


@pytest.mark.vcr()
def test_ask_no_smtp(client, dummy_user, patched_lock):
    with mock.patch("securitas.controller.password.mailer") as mailer:
        mailer.send.side_effect = ConnectionRefusedError
        with mock.patch("securitas.controller.password.app.logger") as logger:
            result = client.post('/forgot-password/ask', data={"username": "dummy"})
    # Email
    mailer.send.assert_called_once()
    # Lock untouched
    patched_lock["store"].assert_not_called()
    # Error message
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="We could not send you an email, please retry later",
        expected_category="danger",
    )
    # Log message
    logger.error.assert_called_once()


def test_ask_still_valid(client, patched_lock_active):
    with mailer.record_messages() as outbox:
        result = client.post('/forgot-password/ask', data={"username": "dummy"})
    # Error message
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    error_message = page.select_one("#formerrors .text-danger")
    assert error_message is not None
    assert error_message.get_text(strip=True).startswith(
        "You have already requested a password reset, you need to wait "
    )
    # No sent email
    assert len(outbox) == 0


def test_change_no_token(client):
    result = client.get('/forgot-password/change')
    assert_redirects_with_flash(
        result,
        expected_url="/forgot-password/ask",
        expected_message="No token provided, please request one.",
        expected_category="warning",
    )


def test_change_invalid_token(client):
    result = client.get('/forgot-password/change?token=this-is-invalid')
    assert_redirects_with_flash(
        result,
        expected_url="/forgot-password/ask",
        expected_message="The token is invalid, please request a new one.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_change_not_active(client, token_for_dummy_user, patched_lock):
    result = client.get(f'/forgot-password/change?token={token_for_dummy_user}')
    patched_lock["delete"].assert_called_once()
    assert_redirects_with_flash(
        result,
        expected_url="/forgot-password/ask",
        expected_message="The token has expired, please request a new one.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_change_too_old(client, token_for_dummy_user, patched_lock):
    passed_expiry = datetime.datetime.now() - datetime.timedelta(minutes=1)
    patched_lock["valid_until"].return_value = passed_expiry
    result = client.get(f'/forgot-password/change?token={token_for_dummy_user}')
    patched_lock["delete"].assert_called_once()
    assert_redirects_with_flash(
        result,
        expected_url="/forgot-password/ask",
        expected_message="The token has expired, please request a new one.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_change_recent_password_change(
    client,
    dummy_user,
    dummy_group,
    token_for_dummy_user,
    no_password_min_time,
    patched_lock_active,
):
    ipa_admin.group_add_member("dummy-group", users="dummy")
    ipa = untouched_ipa_client(current_app)
    ipa.change_password("dummy", "dummy_password", "dummy_password")
    result = client.get(f'/forgot-password/change?token={token_for_dummy_user}')
    patched_lock_active["delete"].assert_called_once()
    assert_redirects_with_flash(
        result,
        expected_url="/forgot-password/ask",
        expected_message=(
            "Your password has been changed since you requested this token, please "
            "request a new one."
        ),
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_change_get(client, dummy_user, token_for_dummy_user, patched_lock_active):
    url = f'/forgot-password/change?token={token_for_dummy_user}'
    result = client.get(url)
    patched_lock_active["delete"].assert_not_called()
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    form = page.select_one(f"form[action='{url}']")
    assert form is not None
    assert len(form.select("input[type='password']")) == 2


@pytest.mark.vcr()
def test_change_post(client, dummy_user, token_for_dummy_user, patched_lock_active):
    with mock.patch("securitas.controller.password.app.logger") as logger:
        result = client.post(
            f'/forgot-password/change?token={token_for_dummy_user}',
            data={"password": "newpassword", "password_confirm": "newpassword"},
        )
    patched_lock_active["delete"].assert_called()
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Your password has been changed.",
        expected_category="success",
    )
    # Log message
    logger.info.assert_called_once()
    log_msg = logger.info.call_args[0][0]
    assert "dummy" in log_msg
    assert "newpassword" not in log_msg


@pytest.mark.vcr()
def test_change_post_password_too_short(
    client, dummy_user, token_for_dummy_user, patched_lock_active
):
    with mock.patch("securitas.controller.password.app.logger") as logger:
        result = client.post(
            f'/forgot-password/change?token={token_for_dummy_user}',
            data={"password": "42", "password_confirm": "42"},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/login",
        expected_message=(
            'Your password has been changed, but it does not comply '
            'with the policy (Constraint violation: Password is too short) and has thus '
            'been set as expired. You will be asked to change it after logging in.'
        ),
        expected_category="warning",
    )
    patched_lock_active["delete"].assert_called()
    logger.info.assert_called_with(
        "Password for dummy was changed to a non-compliant password after completing "
        "the forgotten password process."
    )


@pytest.mark.vcr()
def test_change_post_generic_error(
    client, dummy_user, token_for_dummy_user, patched_lock_active
):
    with mock.patch("securitas.controller.password.app.logger") as logger:
        with mock.patch("securitas.controller.password.ipa_admin") as ipa_admin_mock:
            # We need user_show to work, but make user_mod raise an exception.
            ipa_admin_mock.user_show.side_effect = ipa_admin.user_show
            ipa_admin_mock.user_mod.side_effect = python_freeipa.exceptions.FreeIPAError(
                message="something went wrong", code="4242"
            )
            result = client.post(
                f'/forgot-password/change?token={token_for_dummy_user}',
                data={"password": "newpassword", "password_confirm": "newpassword"},
            )
    assert_form_generic_error(result, 'Could not change password, please try again.')
    logger.error.assert_called_once()
