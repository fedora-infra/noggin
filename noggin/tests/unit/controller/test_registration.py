import datetime

import pytest
import python_freeipa
from fedora_messaging import testing as fml_testing
from flask import current_app

from noggin.app import ipa_admin, mailer
from noggin.representation.user import User
from noggin.signals import stageuser_created, user_registered
from noggin.tests.unit.utilities import (
    assert_form_field_error,
    assert_form_generic_error,
    assert_redirects_with_flash,
)
from noggin.utility.token import Audience, make_token
from noggin_messages import UserCreateV1


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
        "register-underage": "true",
        "register-submit": "1",
    }


@pytest.fixture
def post_data_non_ascii(post_data_step_1):
    post_data_step_1.update(
        {"register-firstname": "习近平 äöü ß", "register-lastname": "ÄÖÜ ẞ 安倍 晋三"}
    )
    return post_data_step_1


@pytest.fixture
def post_data_step_3():
    return {"password": "password", "password_confirm": "password"}


@pytest.fixture
def dummy_stageuser(ipa_testing_config):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    user = ipa_admin.stageuser_add(
        a_uid="dummy",
        o_givenname="Dummy",
        o_sn="User",
        o_cn="Dummy User",
        o_mail="dummy@example.com",
        o_loginshell='/bin/bash',
        fascreationtime=f"{now.isoformat()}Z",
    )['result']
    yield User(user)
    try:
        ipa_admin.stageuser_del(a_uid="dummy")
    except python_freeipa.exceptions.NotFound:
        pass


@pytest.fixture
def token_for_dummy_user(dummy_stageuser):
    return make_token(
        {"sub": dummy_stageuser.username, "mail": dummy_stageuser.mail},
        audience=Audience.email_validation,
        ttl=current_app.config["ACTIVATION_TOKEN_EXPIRATION"],
    )


@pytest.fixture
def spamcheck_on(mocker):
    mocker.patch.dict(current_app.config, {"BASSET_URL": "http://basset.test"})


@pytest.mark.vcr()
def test_step_1(client, post_data_step_1, cleanup_dummy_user, mocker):
    """Register a user, step 1"""
    record_signal = mocker.Mock()
    with mailer.record_messages() as outbox, stageuser_created.connected_to(
        record_signal
    ):
        result = client.post('/', data=post_data_step_1)
    assert result.status_code == 302
    assert result.location == "http://localhost/register/confirm?username=dummy"
    # Emitted signal
    record_signal.assert_called_once()
    # Sent email
    assert len(outbox) == 1
    message = outbox[0]
    assert message.subject == "Verify your email address"
    assert message.recipients == ["dummy@example.com"]
    # Check that default values are added
    user = User(ipa_admin.stageuser_show("dummy")['result'])
    # Creation time
    assert user.creation_time is not None
    # Locale
    assert user.locale == current_app.config["USER_DEFAULTS"]["locale"]
    # Timezone
    assert user.timezone == current_app.config["USER_DEFAULTS"]["timezone"]


@pytest.mark.vcr()
def test_gecos(client, post_data_non_ascii, cleanup_dummy_user, mocker):
    record_signal = mocker.Mock()
    with mailer.record_messages() as _, stageuser_created.connected_to(record_signal):
        result = client.post('/', data=post_data_non_ascii)
    assert result.status_code == 302

    # Check that default values are added
    user = User(ipa_admin.stageuser_show("dummy")['result'])

    assert user.gecos == "Xi Jin Ping aeoeue ss AeOeUe Ss An Bei Jin San"


@pytest.mark.vcr()
def test_step_1_registration_closed(
    client, post_data_step_1, cleanup_dummy_user, mocker
):
    """Try to register a user when registration is closed"""
    mocker.patch.dict(current_app.config, {"REGISTRATION_OPEN": False})
    record_signal = mocker.Mock()
    with mailer.record_messages() as outbox, stageuser_created.connected_to(
        record_signal
    ):
        result = client.post('/', data=post_data_step_1)
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Registration is closed at the moment.",
        expected_category="warning",
    )
    record_signal.assert_not_called()
    assert len(outbox) == 0


@pytest.mark.vcr()
def test_step_1_mixed_case(client, post_data_step_1, mocker):
    """Try to register a user with mixed case username"""
    post_data_step_1["register-username"] = "DummY"
    record_signal = mocker.Mock()
    with mailer.record_messages() as outbox, stageuser_created.connected_to(
        record_signal
    ):
        result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result, "register-username", "Mixed case is not allowed, try lower case."
    )
    record_signal.assert_not_called()
    assert len(outbox) == 0


@pytest.mark.vcr()
def test_step_1_spamcheck(
    client, post_data_step_1, cleanup_dummy_user, spamcheck_on, mocker
):
    """Register a user, step 1, with spamcheck on"""
    mocked_requests = mocker.patch("noggin.signals.requests")
    record_signal = mocker.Mock()
    with mailer.record_messages() as outbox, stageuser_created.connected_to(
        record_signal
    ):
        result = client.post('/', data=post_data_step_1)
    assert result.status_code == 302
    assert result.location == "http://localhost/register/spamcheck-wait?username=dummy"
    # Emitted signal
    record_signal.assert_called_once()
    # Basset called
    mocked_requests.post.assert_called_once()
    assert mocked_requests.post.call_args_list[0][0][0] == "http://basset.test"
    call_data = mocked_requests.post.call_args_list[0][1]["json"]
    assert call_data["action"] == "fedora.noggin.registration"
    assert call_data["data"]["user"]["username"] == "dummy"
    assert call_data["data"]["request_headers"]["Host"] == "localhost"
    assert call_data["data"]["request_ip"] == "127.0.0.1"
    assert "token" in call_data["data"]
    assert call_data["data"]["callback"] == "http://localhost/register/spamcheck-hook"
    # No sent email
    assert len(outbox) == 0


@pytest.mark.parametrize(
    "spamcheck_status", ["spamcheck_awaiting", "spamcheck_denied", "spamcheck_manual"]
)
@pytest.mark.vcr()
def test_spamcheck_wait(client, dummy_stageuser, spamcheck_status):
    """Test the spamcheck_wait endpoint"""
    ipa_admin.stageuser_mod(a_uid="dummy", fasstatusnote=spamcheck_status)
    result = client.get('/register/spamcheck-wait?username=dummy')
    assert result.status_code == 200


@pytest.mark.vcr()
def test_step_2(client, dummy_stageuser):
    """Register a user, step 2"""
    result = client.get('/register/confirm?username=dummy')
    assert result.status_code == 200
    assert "Dummy User" in str(result.data, "utf8")


@pytest.mark.vcr()
def test_step_3(
    client, post_data_step_3, token_for_dummy_user, cleanup_dummy_user, mocker
):
    """Register a user, step 3"""
    record_signal = mocker.Mock()
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ), user_registered.connected_to(record_signal):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Congratulations, your account has been created! Welcome, Dummy User.",
        expected_category="success",
    )
    record_signal.assert_called_once()


@pytest.mark.vcr()
def test_step_1_no_smtp(client, post_data_step_1, cleanup_dummy_user, mocker):
    mailer = mocker.patch("noggin.controller.registration.mailer")
    mailer.send.side_effect = ConnectionRefusedError
    logger = mocker.patch.object(current_app._get_current_object(), "logger")
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
def test_spamcheck_wait_no_username(client, dummy_stageuser):
    """Test the spamcheck_wait endpoint without a username"""
    result = client.get('/register/spamcheck-wait')
    assert result.status_code == 400


@pytest.mark.vcr()
def test_spamcheck_wait_bad_username(client, dummy_stageuser):
    """Test the spamcheck_wait endpoint with a bad username"""
    result = client.get('/register/spamcheck-wait?username=does-not-exist')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="The registration seems to have failed, please try again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_spamcheck_wait_active(client, dummy_stageuser):
    """Test the spamcheck_wait endpoint when the user is active"""
    ipa_admin.stageuser_mod(a_uid="dummy", fasstatusnote="active")
    result = client.get('/register/spamcheck-wait?username=dummy')
    assert result.status_code == 302
    assert result.location == "http://localhost/register/confirm?username=dummy"


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
def test_step_2_spamchecking_user(client, dummy_stageuser, spamcheck_on):
    """Register a user, step 2, but the user hasn't been checked for spam"""
    ipa_admin.stageuser_mod(a_uid="dummy", fasstatusnote="spamcheck_awaiting")
    result = client.get('/register/confirm?username=dummy')
    assert result.status_code == 401


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
def test_step_3_invalid_token(client, dummy_stageuser, mocker):
    """Registration activation page with an invalid token"""
    token = make_token(
        {"sub": dummy_stageuser.username, "mail": dummy_stageuser.mail},
        audience=Audience.email_validation,
        ttl=-1,
    )
    result = client.get(f'/register/activate?token={token}')
    assert_redirects_with_flash(
        result,
        expected_url="/?tab=register",
        expected_message="This token is no longer valid, please register again.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_step_3_unknown_user(client, token_for_dummy_user):
    """Registration activation page with a token pointing to an unknown user"""
    ipa_admin.stageuser_del(a_uid="dummy")
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
    logger = mocker.patch.object(current_app._get_current_object(), "logger")
    ipa_admin.stageuser_mod(a_uid="dummy", mail="dummy-new@example.com")
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
    client, post_data_step_3, token_for_dummy_user, cleanup_dummy_user, mocker
):
    """Register a user with a password rejected by the server policy"""
    record_signal = mocker.Mock()
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ), user_registered.connected_to(record_signal):
        post_data_step_3["password"] = post_data_step_3["password_confirm"] = "1234567"
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
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
    record_signal.assert_called_once()


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
    user = User(ipa_admin.stageuser_show(a_uid="dummy")['result'])
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
    record_signal = mocker.Mock()
    with fml_testing.mock_sends(UserCreateV1), user_registered.connected_to(
        record_signal
    ):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_form_field_error(
        result, field_name="password", expected_message="this is invalid"
    )
    record_signal.assert_called_once()


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


@pytest.mark.vcr()
def test_underage(client, post_data_step_1):
    """Register a user that is too young"""
    post_data_step_1["register-underage"] = ""
    result = client.post('/', data=post_data_step_1)
    assert_form_field_error(
        result,
        field_name="register-underage",
        expected_message="You must be over 16 years old to create an account",
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
        'Something went wrong while creating your account, please try again later.',
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
    record_signal = mocker.Mock()
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ), user_registered.connected_to(record_signal):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
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
    record_signal.assert_called_once()


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
    record_signal = mocker.Mock()
    with fml_testing.mock_sends(
        UserCreateV1({"msg": {"agent": "dummy", "user": "dummy"}})
    ), user_registered.connected_to(record_signal):
        result = client.post(
            f"/register/activate?token={token_for_dummy_user}", data=post_data_step_3
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message=(
            "Congratulations, your account has been created! Go ahead and sign in to proceed."
        ),
        expected_category="success",
    )
    record_signal.assert_called_once()


@pytest.mark.parametrize(
    "spamcheck_status", ["active", "spamcheck_denied", "spamcheck_manual"]
)
@pytest.mark.vcr()
def test_spamcheck(client, dummy_stageuser, mocker, spamcheck_status, spamcheck_on):
    user = User(ipa_admin.stageuser_show("dummy")["result"])
    assert user.status_note != spamcheck_status
    token = make_token({"sub": "dummy"}, audience=Audience.spam_check)
    with mailer.record_messages() as outbox:
        response = client.post(
            "/register/spamcheck-hook",
            json={"token": token, "status": spamcheck_status},
        )
    assert response.status_code == 200
    assert response.json == {"status": "success"}
    # Check that the status was changed
    user = User(ipa_admin.stageuser_show("dummy")["result"])
    assert user.status_note == spamcheck_status
    # Sent email
    if spamcheck_status == "active":
        assert len(outbox) == 1
        message = outbox[0]
        assert message.subject == "Verify your email address"
        assert message.recipients == ["dummy@example.com"]
    else:
        assert len(outbox) == 0


@pytest.mark.vcr()
def test_spamcheck_disabled(client, dummy_user):
    response = client.post(
        "/register/spamcheck-hook", json={"token": "foobar", "status": "active"},
    )
    assert response.status_code == 501
    assert response.json == {"error": "Spamcheck disabled"}


@pytest.mark.vcr()
def test_spamcheck_bad_payload(client, dummy_user, mocker, spamcheck_on):
    response = client.post("/register/spamcheck-hook")
    assert response.status_code == 400
    assert response.json == {"error": "Bad payload"}


@pytest.mark.parametrize("payload", [{"token": "foobar"}, {"status": "active"}])
@pytest.mark.vcr()
def test_spamcheck_bad_missing_key(client, dummy_user, mocker, payload, spamcheck_on):
    response = client.post("/register/spamcheck-hook", json=payload,)
    assert response.status_code == 400
    assert response.json["error"].startswith("Missing key: ")


@pytest.mark.vcr()
def test_spamcheck_expired_token(client, dummy_user, mocker, spamcheck_on):
    token = make_token({"sub": "dummy"}, audience=Audience.spam_check, ttl=-1)
    response = client.post(
        "/register/spamcheck-hook", json={"token": token, "status": "active"},
    )
    assert response.status_code == 400
    assert response.json == {"error": "The token has expired"}


@pytest.mark.vcr()
def test_spamcheck_invalid_token(client, dummy_user, mocker, spamcheck_on):
    token = make_token({"sub": "dummy"}, audience=Audience.email_validation)
    response = client.post(
        "/register/spamcheck-hook", json={"token": token, "status": "active"},
    )
    assert response.status_code == 400
    assert response.json["error"] == "Invalid token: Invalid audience"


@pytest.mark.vcr()
def test_spamcheck_wrong_status(client, dummy_user, mocker, spamcheck_on):
    token = make_token({"sub": "dummy"}, audience=Audience.spam_check)
    response = client.post(
        "/register/spamcheck-hook", json={"token": token, "status": "this-is-wrong"},
    )
    assert response.status_code == 400
    assert response.json == {"error": "Invalid status: this-is-wrong."}
