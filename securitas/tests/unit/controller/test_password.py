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


def test_missing_credentials(client):
    """Verify that missing details are caught"""
    result = client.post(
        '/password-reset',
        data={
            "username": "",
            "current_password": "",
            "password": "",
            "password_confirm": "",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Please fill in all fields to reset your password'


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
    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Password and confirmation did not match.'


def test_password_policy(client):
    """Verify that password policies are upheld"""
    result = client.post(
        '/password-reset',
        data={ 
            "username": "jbloggs",
            "current_password": "1",
            "password": "LongSuperSafePassword",
            "password_confirm": "LongSuperSafePassword",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Failed to reset your password (invalid current password).'

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
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Failed to reset your password (policy error): Constraint violation: Too soon to change password'

@pytest.mark.vcr()
def test_incorrect_current_password(client):
    """Verify that current password must be correct"""
    result = client.post(
        '/password-reset',
        data={
            "username": "testuser",
            "current_password": "thisisnotthecorrectspassword",
            "password": "1",
            "password_confirm": "1",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Failed to reset your password (invalid current password).'

@pytest.mark.vcr()
def test_password_changes(client):
    """Verify that password changes"""
    result = client.post(
        '/password-reset',
        data={
            "username": "testuser",
            "current_password": "testuserpw",
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
