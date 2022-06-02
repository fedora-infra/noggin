from unittest import mock
from urllib.parse import quote

import pytest
import python_freeipa
import requests
from bs4 import BeautifulSoup
from flask import current_app, get_flashed_messages, session

from noggin.app import ipa_admin

from ..utilities import (
    assert_form_field_error,
    assert_form_generic_error,
    assert_redirects_with_flash,
    get_otp,
    otp_secret_from_uri,
)


@pytest.fixture
def dummy_user_expired_password():
    ipa_admin.user_add(
        'dummy',
        o_givenname='Dummy',
        o_sn='User',
        o_cn='Dummy User',
        o_userpassword='dummy_password',
        o_loginshell='/bin/bash',
    )
    # Don't change the password: it will be expired
    yield
    ipa_admin.user_del(a_uid='dummy')


# Logout
@pytest.mark.vcr()
def test_logout_unauthed(client):
    """Test logout when not logged in"""
    result = client.get('/logout', follow_redirects=False)
    assert result.status_code == 302
    assert result.location == "/"
    # Make sure we haven't instructed the user to login in a flash message.
    messages = get_flashed_messages()
    assert len(messages) == 0


@pytest.mark.vcr()
def test_logout(client, logged_in_dummy_user):
    """Test logout with a logged-in user"""
    result = client.get('/logout', follow_redirects=False)
    assert result.status_code == 302
    assert result.location == "/"
    assert "noggin_session" not in session
    assert "noggin_username" not in session
    assert "noggin_ipa_server_hostname" not in session


@pytest.mark.vcr()
def test_logout_no_ipa(client, mocker):
    """Test logout when IPA can't be reached"""
    maybe_ipa_session = mocker.patch("noggin.controller.root.maybe_ipa_session")
    maybe_ipa_session.side_effect = python_freeipa.exceptions.FreeIPAError

    # Flask request, session, ... objects don't cope well with being inspected which is
    # what unittest.mock does from Python 3.8 on. Plant something certifiably stupid and
    # forgiving instead.
    session = mocker.patch("noggin.controller.root.session", new=mock.MagicMock())

    result = client.get('/logout', follow_redirects=False)
    assert result.status_code == 302
    assert result.location == "/"
    # Make sure we did clear the session
    session.clear.assert_called_once()


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
        follow_redirects=False,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/",
        expected_message="Welcome, dummy!",
        expected_category="success",
    )
    assert session.get("noggin_username") == "dummy"
    assert session.get("noggin_session") is not None


@pytest.mark.vcr()
def test_login_with_otp(client, dummy_user_with_otp):
    """Test a successful Login with password + otp"""
    otp = get_otp(otp_secret_from_uri(dummy_user_with_otp.uri))
    result = client.post(
        '/',
        data={
            "login-username": "dummy",
            "login-password": "dummy_password",
            "login-otp": otp,
            "login-submit": "1",
        },
        follow_redirects=False,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/",
        expected_message="Welcome, dummy!",
        expected_category="success",
    )
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


@pytest.mark.vcr()
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


@pytest.mark.vcr()
def test_login_username_case(client, dummy_user):
    """Test giving username random uppercase letter"""
    result = client.post(
        '/',
        data={
            "login-username": "duMmy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
    )
    assert_form_field_error(
        result,
        "login-username",
        "Mixed case is not allowed, try lower case.",
    )


@pytest.mark.vcr()
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


@pytest.mark.parametrize(
    "username", ["dummy_user", "dummy.user", "_dummy", ".dummy", "dummy-"]
)
def test_login_bad_format(client, mocker, username):
    """Let users login even if they registered with a username that is now invalid"""
    maybe_ipa_login = mocker.patch("noggin.controller.authentication.maybe_ipa_login")
    result = client.post(
        '/',
        data={
            "login-username": username,
            "login-password": "dummy_password",
            "login-submit": "1",
        },
        follow_redirects=False,
    )
    assert_redirects_with_flash(
        result,
        expected_url=f"/user/{username}/",
        expected_message=f"Welcome, {username}!",
        expected_category="success",
    )
    maybe_ipa_login.assert_called()
    assert maybe_ipa_login.call_args_list[0][0][2] == username


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


@pytest.mark.vcr()
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


@pytest.mark.vcr()
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
def test_login_form_redirect(client):
    """Test that the login form has redirect information"""
    redirect_url = "/groups/?page_size=30&page_number=2"
    url = f"/?next={quote(redirect_url)}"
    result = client.get(url)
    page = BeautifulSoup(result.data, 'html.parser')
    forms = page.select("form")
    for form in forms:
        if form["action"] == url:
            break
    else:
        assert False, "No form found with the expected action"


@pytest.mark.vcr()
def test_login_with_redirect(client, dummy_user):
    """Test a successful login with a redirect"""
    redirect_url = "/groups/?page_size=30&page_number=2"
    result = client.post(
        f"/?next={quote(redirect_url)}",
        data={
            "login-username": "dummy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
    )
    assert_redirects_with_flash(result, redirect_url, "Welcome, dummy!", "success")


@pytest.mark.vcr()
def test_login_with_bad_redirect(client, dummy_user):
    """Test a successful login with a bad redirect"""
    redirect_url = "http://unit.tests"
    result = client.post(
        f"/?next={quote(redirect_url)}",
        data={
            "login-username": "dummy",
            "login-password": "dummy_password",
            "login-submit": "1",
        },
    )
    assert_redirects_with_flash(result, "/user/dummy/", "Welcome, dummy!", "success")


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


@pytest.mark.skip("IPA never fails anymore on invalid token sync")
@pytest.mark.vcr()
def test_otp_sync_invalid_codes(client, logged_in_dummy_user_with_otp):
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
def test_otp_sync_http_error(client, logged_in_dummy_user_with_otp, mocker):
    """Test synchronising OTP token with mocked http error"""
    logger = mocker.patch.object(current_app._get_current_object(), "logger")
    method = mocker.patch("requests.sessions.Session.post")
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
def test_otp_sync_rejected(client, logged_in_dummy_user_with_otp):
    """Test synchronising OTP token when freeipa rejects the request"""
    session = mock.Mock()
    with mock.patch("python_freeipa.client.requests.Session", return_value=session):
        session.post.return_value.status_code = 200
        session.post.return_value.text = "Token sync rejected"
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
def test_otp_sync_success(client, logged_in_dummy_user_with_otp):
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
