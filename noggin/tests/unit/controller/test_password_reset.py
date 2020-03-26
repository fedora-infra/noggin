from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup

from noggin import ipa_admin
from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
)


def test_password_reset(client):
    """Test the password reset page"""
    result = client.get('/password-reset?username=fred')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Expired Password Reset - noggin'


def test_password_reset_no_username(client):
    """Test the password reset page with no username """
    result = client.get('/password-reset')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_password_reset_user(client, logged_in_dummy_user):
    """Test the redirect to the authed password reset"""
    result = client.get('/password-reset')
    assert result.location == f"http://localhost/user/dummy/settings/password"

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
def test_password_changes_user(
    client, logged_in_dummy_user, dummy_group, no_password_min_time
):
    """Verify that password changes"""
    ipa_admin.group_add_member("dummy-group", users="dummy")
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
        follow_redirects=True,
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
        follow_redirects=True,
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
        follow_redirects=True,
    )
    assert_form_field_error(
        result,
        field_name="current_password",
        expected_message="The old password or username is not correct",
    )


@pytest.mark.vcr()
def test_time_sensitive_password_policy(client, dummy_user):
    """Verify that new password policies are upheld"""
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "somesupersecretpassword",
            "password_confirm": "somesupersecretpassword",
        },
        follow_redirects=True,
    )
    # the dummy user is created and has its password immediately changed,
    # so this next attempt should failt with a constraint error.
    assert_form_field_error(
        result,
        field_name="password",
        expected_message="Constraint violation: Too soon to change password",
    )


@pytest.mark.vcr()
def test_short_password(client, dummy_user, no_password_min_time):
    """Verify that new password policies are upheld"""
    result = client.post(
        '/password-reset?username=dummy',
        data={
            "current_password": "dummy_password",
            "password": "1",
            "password_confirm": "1",
        },
        follow_redirects=True,
    )
    assert_form_field_error(
        result,
        field_name="password",
        expected_message="Constraint violation: Password is too short",
    )


def test_reset_generic_error(client):
    """Reset password with an unhandled error"""
    client_mock = mock.Mock()
    with mock.patch(
        "noggin.controller.password.untouched_ipa_client"
    ) as untouched_ipa_client:
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
def test_password_changes(client, dummy_user, no_password_min_time):
    """Verify that password changes"""
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
