import datetime

import pytest
import python_freeipa
from fedora_messaging import testing as fml_testing
from flask import current_app
from noggin_messages import UserCreateV1

from noggin import ipa_admin, mailer
from noggin.representation.user import User
from noggin.utility.token import EmailValidationToken
from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
)


@pytest.fixture
def cleanup_dummy_user():
    yield
    for user_type in ("user", "stageuser"):
        try:
            getattr(ipa_admin, f"{user_type}_del")('dummy')
        except python_freeipa.exceptions.NotFound:
            pass


@pytest.fixture
def post_data_step_1():
    return {
        "register-firstname": "Dummy",
        "register-lastname": "User",
        "register-mail": "dummy@example.com",
        "register-username": "dummy",
        "register-submit": "1",
    }


@pytest.fixture
def post_data_step_3():
    return {"password": "password", "password_confirm": "password"}


@pytest.fixture
def dummy_stageuser(ipa_testing_config):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    user = ipa_admin.stageuser_add(
        "dummy",
        "Dummy",
        'User',
        mail="dummy@example.com",
        login_shell='/bin/bash',
        fascreationtime=f"{now.isoformat()}Z",
    )
    yield User(user)
    try:
        ipa_admin.stageuser_del("dummy")
    except python_freeipa.exceptions.NotFound:
        pass


@pytest.fixture
def token_for_dummy_user(dummy_stageuser):
    token = EmailValidationToken.from_user(dummy_stageuser)
    return token.as_string()


@pytest.mark.vcr()
def test_step_1(client, post_data_step_1, cleanup_dummy_user):
    """Register a user, step 1"""
    with mailer.record_messages() as outbox:
        result = client.post('/', data=post_data_step_1)
    assert result.status_code == 302
    assert result.location == "http://localhost/register/confirm?username=dummy"
    # Sent email
    assert len(outbox) == 1
    message = outbox[0]
    assert message.subject == "Verify your email address"
    assert message.recipients == ["dummy@example.com"]
    # Check that default values are added
    user = ipa_admin.stageuser_show("dummy")
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


@pytest.mark.vcr()
def test_step_2(client, dummy_stageuser):
    """Register a user, step 2"""
    result = client.get('/register/confirm?username=dummy')
    assert result.status_code == 200
    assert "Dummy User" in str(result.data, "utf8")


@pytest.mark.vcr()
def test_step_3(client, post_data_step_3, token_for_dummy_user, cleanup_dummy_user):
    """Register a user, step 3"""
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        "/",
        "Congratulations, your account is now active! Welcome, Dummy User.",
        "success",
    )


@pytest.mark.vcr()
def test_step_1_no_smtp(client, post_data_step_1, cleanup_dummy_user, mocker):
    mailer = mocker.patch("noggin.controller.registration.mailer")
    mailer.send.side_effect = ConnectionRefusedError
    logger = mocker.patch("noggin.controller.registration.app.logger")
    result = client.post('/', data=post_data_step_1)
    # Error message
    assert_redirects_with_flash(
        result,
        expected_url="/register/confirm?username=dummy",
        expected_message="We could not send you the address validation email, please retry later",
        expected_category="danger",
    )
    # Log message
    logger.error.assert_called_once()


@pytest.mark.vcr()
def test_step_2_no_user(client):
    """Register a user, step 2, but no provided username"""
    result = client.get('/register/confirm')
    assert result.status_code == 400
    assert "No username provided" in str(result.data, "utf8")


@pytest.mark.vcr()
def test_step_2_unknown_user(client):
    """Register a user, step 2, but no provided username"""
    result = client.get('/register/confirm?username=unknown')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="The registration seems to have failed, please try again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_2_resend(client, dummy_stageuser):
    """Register a user, step 2, but no provided username"""
    with mailer.record_messages() as outbox:
        result = client.post('/register/confirm?username=dummy', data={"submit": "1"})
    assert_redirects_with_flash(
        result,
        expected_url="/register/confirm?username=dummy",
        expected_message=(
            "The address validation email has be sent again. Make sure it did not land "
            "in your spam folder"
        ),
        expected_category="success",
    )
    # Sent email
    assert len(outbox) == 1
    message = outbox[0]
    assert message.subject == "Verify your email address"
    assert message.recipients == ["dummy@example.com"]


@pytest.mark.vcr()
def test_step_3_no_token(client, dummy_stageuser):
    """Registration activation page but no token"""
    result = client.get('/register/activate')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="No token provided, please check your email validation link.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_3_garbled_token(client, dummy_stageuser):
    """Registration activation page with a bad token"""
    result = client.get('/register/activate?token=pants')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="The token is invalid, please register again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_3_invalid_token(client, token_for_dummy_user, mocker):
    """Registration activation page with an invalid token"""
    mocker.patch(
        "noggin.controller.registration.EmailValidationToken.is_valid",
        return_value=False,
    )
    result = client.get(f'/register/activate?token={token_for_dummy_user}')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="This token is no longer valid, please register again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_3_unknown_user(client, token_for_dummy_user):
    """Registration activation page with a token pointing to an unknown user"""
    ipa_admin.stageuser_del("dummy")
    result = client.get(f'/register/activate?token={token_for_dummy_user}')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="This user cannot be found, please register again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_3_wrong_address(client, token_for_dummy_user, mocker):
    """Registration activation page with a token containing the wrong email address"""
    logger = mocker.patch("noggin.controller.registration.app.logger")
    ipa_admin.stageuser_mod("dummy", mail="dummy-new@example.com")
    result = client.get(f'/register/activate?token={token_for_dummy_user}')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message=(
            "The username and the email address don't match the token you used, "
            "please register again."
        ),
        expected_category="warning",
    )
    logger.error.assert_called_once()


@pytest.mark.vcr()
def test_short_password_form(
    client, post_data_step_3, token_for_dummy_user, cleanup_dummy_user, mocker
):
    """Register a user with too short a password"""
    post_data_step_3["password"] = post_data_step_3["password_confirm"] = "42"
    result = client.post(
        f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
    )
    assert_form_field_error(
        result, "password", expected_message='Field must be at least 6 characters long.'
    )


@pytest.mark.vcr()
def test_short_password_policy(
    client, post_data_step_3, token_for_dummy_user, cleanup_dummy_user
):
    """Register a user with a password rejected by the server policy"""
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        post_data_step_3["password"] = post_data_step_3["password_confirm"] = "1234567"
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            'Your account has been activated, but the password you chose does not comply '
            'with the policy (Constraint violation: Password is too short) and has thus '
            'been set as expired. You will be asked to change it after logging in.'
        ),
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_duplicate(client, post_data_step_1, cleanup_dummy_user, dummy_user):
    """Register a user that already exists"""
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result,
        field_name="register-username",
        expected_message='This username is already taken, please choose another one.',
    )


@pytest.mark.vcr()
def test_invalid_username(client, post_data_step_1):
    """Register a user with an invalid username"""
    post_data_step_1["register-username"] = "this is invalid"
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result,
        field_name="register-username",
        expected_message='may only include letters, numbers, _, -, . and $',
    )


@pytest.mark.parametrize("field_name", ["firstname", "lastname"])
@pytest.mark.vcr()
def test_strip(client, post_data_step_1, cleanup_dummy_user, field_name):
    """Register a user with fields that contain trailing spaces"""
    post_data_step_1[f"register-{field_name}"] = "Dummy "
    with mailer.record_messages() as outbox:
        result = client.post('/', data=post_data_step_1)
    assert result.status_code == 302, str(result.data, "utf8")
    user = User(ipa_admin.stageuser_show("dummy"))
    assert getattr(user, field_name) == "Dummy"
    assert len(outbox) == 1


@pytest.mark.parametrize(
    "field_name,server_name",
    [
        ("username", "login"),
        ("firstname", "first"),
        ("lastname", "last"),
        ("mail", "email"),
    ],
)
def test_field_error_step_1(client, post_data_step_1, mocker, field_name, server_name):
    """Register a user with fields that the server errors on"""
    ipa_admin = mocker.patch("noggin.controller.registration.ipa_admin")
    ipa_admin.stageuser_add.side_effect = python_freeipa.exceptions.ValidationError(
        message=f"invalid '{server_name}': this is invalid", code="4242"
    )
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result, field_name=f"register-{field_name}", expected_message="this is invalid"
    )


@pytest.mark.vcr()
def test_field_error_step_3(
    client, token_for_dummy_user, mocker, post_data_step_3, cleanup_dummy_user
):
    """Activate a user with a password that the server errors on"""
    user_mod = mocker.patch("noggin.controller.registration.ipa_admin.user_mod")
    user_mod.side_effect = python_freeipa.exceptions.ValidationError(
        message="invalid 'password': this is invalid", code="4242"
    )
    result = client.post(
        f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
    )
    assert_form_field_error(
        result, field_name="password", expected_message="this is invalid"
    )


def test_field_error_unknown(client, post_data_step_1, mocker):
    """Register a user with fields that the server errors on, but it's unknown to us"""
    ipa_admin = mocker.patch("noggin.controller.registration.ipa_admin")
    ipa_admin.stageuser_add.side_effect = python_freeipa.exceptions.ValidationError(
        message="invalid 'unknown': this is invalid", code="4242"
    )
    result = client.post('/', data=post_data_step_1)
    assert_form_generic_error(
        result, expected_message="invalid 'unknown': this is invalid"
    )


def test_invalid_first_name(client, post_data_step_1, mocker):
    """Register a user with an invalid first name"""
    ipa_admin = mocker.patch("noggin.controller.registration.ipa_admin")
    ipa_admin.stageuser_add.side_effect = python_freeipa.exceptions.ValidationError(
        message="invalid first name", code="4242"
    )
    post_data_step_1["register-firstname"] = "This \n is \n invalid"
    result = client.post('/', data=post_data_step_1)
    assert_form_generic_error(result, 'invalid first name')


@pytest.mark.vcr()
def test_invalid_email(client, post_data_step_1):
    """Register a user with an invalid email address"""
    post_data_step_1["register-mail"] = "firstlast at name dot org"
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result, field_name="register-mail", expected_message='Email must be valid'
    )


@pytest.mark.vcr()
def test_blocklisted_email(client, post_data_step_1):
    """Register a user with an invalid email address"""
    post_data_step_1["register-mail"] = "dude@fedoraproject.org"
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result,
        field_name="register-mail",
        expected_message='Email addresses from that domain are not allowed',
    )


@pytest.mark.vcr()
def test_empty_email(client, post_data_step_1):
    """Register a user with an empty email address"""
    del post_data_step_1["register-mail"]
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result, field_name="register-mail", expected_message='Email must not be empty'
    )


def test_generic_error(client, post_data_step_1, mocker):
    """Register a user with an unhandled error"""
    ipa_admin = mocker.patch("noggin.controller.registration.ipa_admin")
    ipa_admin.stageuser_add.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    result = client.post('/', data=post_data_step_1)
    assert_form_generic_error(
        result, 'An error occurred while creating the account, please try again.'
    )


@pytest.mark.vcr()
def test_generic_activate_error(
    client, token_for_dummy_user, post_data_step_3, cleanup_dummy_user, mocker
):
    """Activate the user with an unhandled error"""
    ipa_admin_activate = mocker.patch(
        "noggin.controller.registration.ipa_admin.stageuser_activate"
    )
    ipa_admin_activate.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    with fml_testing.mock_sends():
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_form_generic_error(
        result,
        'Something went wrong while activating your account, please try again later.',
    )


@pytest.mark.vcr()
def test_generic_pwchange_error(
    client, token_for_dummy_user, post_data_step_3, cleanup_dummy_user, mocker
):
    """Change user's password with an unhandled error"""
    ipa_client = mocker.Mock()
    ipa_client.change_password.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    untouched_ipa_client = mocker.patch(
        "noggin.controller.registration.untouched_ipa_client"
    )
    untouched_ipa_client.return_value = ipa_client
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            'Your account has been activated, but an error occurred while setting your '
            'password (something went wrong). You may need to change it after logging in.'
        ),
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_no_direct_login(
    client, token_for_dummy_user, post_data_step_3, cleanup_dummy_user, mocker
):
    """Failure logging the user in directly"""
    mocker.patch(
        "noggin.controller.registration.maybe_ipa_login",
        side_effect=python_freeipa.exceptions.FreeIPAError(
            message="something went wrong", code="4242"
        ),
    )
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            "Congratulations, your account is now active! Go ahead and sign in to proceed."
        ),
        expected_category="success",
    )
