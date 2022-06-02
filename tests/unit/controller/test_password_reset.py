import pytest
import python_freeipa
from bs4 import BeautifulSoup
from fedora_messaging import testing as fml_testing

from noggin.app import ipa_admin
from noggin_messages import UserUpdateV1

from ..utilities import (
    assert_form_field_error,
    assert_form_generic_error,
    assert_redirects_with_flash,
)


def test_password_reset(client):
    """Test the password reset page"""
    result = client.get('/password-reset?username=fred')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Expired Password Reset - noggin'


def test_password_reset_no_username(client):
    """Test the password reset page with no username"""
    result = client.get('/password-reset')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_password_reset_user(client, logged_in_dummy_user):
    """Test the redirect to the authed password reset"""
    result = client.get('/password-reset')
    assert result.location == "/user/dummy/settings/password"

    result = client.get('/password-reset', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    pageheading = page.select("#pageheading")[0]
    assert pageheading.get_text(strip=True) == "Change Password"


@pytest.mark.vcr()
def test_password_changes_wrong_user(client, logged_in_dummy_user):
    """Verify that we error if trying to change another user's password"""
    result = client.post(
        '/user/admin/settings/password',
        data={
            "username": "admin",
            "current_password": "dummy_password",
            "password": "secretpw",
            "password_confirm": "secretpw",
        },
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/admin/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_password_changes_user(client, logged_in_dummy_user):
    """Verify that password changes"""
    with fml_testing.mock_sends(
        UserUpdateV1(
            {"msg": {"agent": "dummy", "user": "dummy", "fields": ["password"]}}
        )
    ):
        result = client.post(
            '/user/dummy/settings/password',
            data={
                "username": "dummy",
                "current_password": "dummy_password",
                "password": "secretpw",
                "password_confirm": "secretpw",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Your password has been changed",
        expected_category="success",
    )


@pytest.mark.vcr()
def test_password_form_with_otp(client, logged_in_dummy_user_with_otp):
    """Verify that the password change form shows OTP form elements
    when a user has OTP enabled"""
    result = client.get("/user/dummy/settings/password")

    page = BeautifulSoup(result.data, "html.parser")
    otpinput = page.select("#otpinput")
    assert len(otpinput) == 1


@pytest.mark.vcr()
def test_password_form_without_otp(client, logged_in_dummy_user):
    """Verify that the password change form shows OTP form elements
    when a user has OTP disabled"""
    result = client.get("/user/dummy/settings/password")

    page = BeautifulSoup(result.data, "html.parser")

    currentpasswordinput = page.select("#currentpasswordinput .form-text .text-muted")
    assert len(currentpasswordinput) == 0

    otpinput = page.select("#otpinput .form-text .text-muted")

    assert len(otpinput) == 0


@pytest.mark.vcr()
def test_non_matching_passwords_user(client, logged_in_dummy_user):
    """Verify that passwords that dont match are caught"""
    result = client.post(
        '/user/dummy/settings/password',
        data={
            "username": "jbloggs",
            "current_password": "sdsds",
            "password": "password1",
            "password_confirm": "password2",
        },
    )
    assert_form_field_error(
        result, field_name="password", expected_message="Passwords must match"
    )


@pytest.mark.vcr()
def test_password_user(client, logged_in_dummy_user):
    """Verify that current password must be correct"""
    result = client.post(
        '/user/dummy/settings/password',
        data={
            "username": "dummy",
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
    )
    assert_form_field_error(
        result,
        field_name="current_password",
        expected_message="The old password or username is not correct",
    )


def test_non_matching_passwords(client):
    """Verify that passwords that dont match are caught"""
    result = client.post(
        '/password-reset?username=jbloggs',
        data={
            "current_password": "sdsds",
            "password": "password1",
            "password_confirm": "password2",
        },
    )
    assert_form_field_error(
        result, field_name="password", expected_message="Passwords must match"
    )


@pytest.mark.vcr()
def test_password(client, dummy_user):
    """Verify that current password must be correct"""
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
    )
    assert_form_field_error(
        result,
        field_name="current_password",
        expected_message="The old password or username is not correct",
    )


@pytest.mark.vcr()
def test_password_no_user(client):
    """Verify that user must exist"""
    result = client.post(
        '/password-reset?username=dudemcpants',
        data={
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
    )
    assert_form_field_error(
        result,
        field_name="current_password",
        expected_message="The old password or username is not correct",
    )


@pytest.mark.vcr()
def test_time_sensitive_password_policy(client, dummy_user, password_min_time):
    """Verify that new password policies are upheld"""
    ipa_admin.group_add_member(a_cn="dummy-group", o_user="dummy")
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "somesupersecretpassword",
            "password_confirm": "somesupersecretpassword",
        },
    )
    # the dummy user is created and has its password immediately changed,
    # so this next attempt should fail with a constraint error.
    assert_form_field_error(
        result,
        field_name="password",
        expected_message="Constraint violation: Too soon to change password",
    )


@pytest.mark.vcr()
def test_short_password_form(client, dummy_user):
    """Verify that form password policies are upheld"""
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "1",
            "password_confirm": "1",
        },
    )
    assert_form_field_error(
        result,
        field_name="password",
        expected_message="Field must be at least 6 characters long.",
    )


@pytest.mark.vcr()
def test_short_password_policy(client, dummy_user):
    """Verify that server password policies are upheld"""
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "1234567",
            "password_confirm": "1234567",
        },
    )
    assert_form_field_error(
        result,
        field_name="password",
        expected_message="Constraint violation: Password is too short",
    )


def test_reset_generic_error(client, mocker):
    """Reset password with an unhandled error"""
    client_mock = mocker.Mock()
    untouched_ipa_client = mocker.patch(
        "noggin.controller.password.untouched_ipa_client"
    )
    untouched_ipa_client.return_value = client_mock
    client_mock.change_password.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="something went wrong", code="4242"
    )
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "password",
            "password_confirm": "password",
        },
    )
    assert_form_generic_error(result, 'Could not change password.')


@pytest.mark.vcr()
def test_password_changes(client, dummy_user):
    """Verify that password changes"""
    with fml_testing.mock_sends(
        UserUpdateV1(
            {"msg": {"agent": "dummy", "user": "dummy", "fields": ["password"]}}
        )
    ):
        result = client.post(
            '/password-reset?username=dummy',
            data={
                "current_password": "dummy_password",
                "password": "secretpw",
                "password_confirm": "secretpw",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Your password has been changed",
        expected_category="success",
    )
