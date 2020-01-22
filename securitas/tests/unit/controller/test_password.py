import pytest
from bs4 import BeautifulSoup
from securitas import ipa_admin


def test_password_reset(client):
    """Test the password reset page"""

    # check that when unauthed, we redirect back to /
    result = client.get('/password-reset')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Password Reset - The Fedora Project'


def test_non_matching_passwords(client):
    """Verify that passwords that dont match are caught"""
    result = client.post(
        '/password-reset',
        data={
            "username": "jbloggs",
            "current_password": "sdsds",
            "password": "password1",
            "password_confirm": "password2",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'invalid' in password_input['class']
    helper_text = password_input.find_next("span", class_="helper-text")
    assert helper_text["data-error"] == "Passwords must match"

@pytest.mark.vcr()
def test_password(client):
    """Verify that current password must be correct"""
    result = client.post(
        '/password-reset',
        data={ 
            "username": "admin",
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='current_password']")[0]
    assert 'invalid' in password_input['class']
    helper_text = password_input.find_next("span", class_="helper-text")
    assert helper_text["data-error"] == "The old password or username is not correct"


@pytest.mark.vcr()
def test_time_sensitive_password_policy(client, dummy_user):
    """Verify that new password policies are upheld"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "dummy_password",
            "password": "1",
            "password_confirm": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    password_input = page.select("input[name='password']")[0]
    assert 'invalid' in password_input['class']
    helper_text = password_input.find_next("span", class_="helper-text")
    assert helper_text["data-error"] == "Constraint violation: Too soon to change password"


@pytest.mark.vcr()
def test_password_changes(client, dummy_user_as_group_manager, remove_password_min_time):
    """Verify that password changes"""
    result = client.post(
        '/password-reset',
        data={
            "username": "dummy",
            "current_password": "dummy_password",
            "password": "secretpw",
            "password_confirm": "secretpw",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .green")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Your password has been changed, please try to log in with the new one now.'
