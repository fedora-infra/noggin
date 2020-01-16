import pytest
from bs4 import BeautifulSoup


def test_logout(client):
    """Test logout"""
    # check that when unauthed, we redirect back to /
    result = client.get('/logout', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'


@pytest.mark.vcr()
def test_login(client):
    """Test a successful Login"""
    result = client.post(
        '/login',
        data={"username": "dudemcpants", "password": "n:nPv{P].9}]!q$RE%w<38@",},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')

    messages = page.select(".flash-messages .green")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Welcome, dudemcpants!'


def test_login_no_password(client):
    """Test not giving a password"""
    result = client.post(
        '/login', data={"username": "dudemcpants",}, follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')

    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert (
        messages[0].get_text(strip=True)
        == 'Please provide both a username and a password.'
    )


def test_login_no_username(client):
    """Test not giving a password"""
    result = client.post(
        '/login', data={"password": "n:nPv{P].9}]!q$RE%w<38@",}, follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')

    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert (
        messages[0].get_text(strip=True)
        == 'Please provide both a username and a password.'
    )


@pytest.mark.vcr()
def test_login_incorrect_password(client):
    """Test a incorrect password"""
    result = client.post(
        '/login',
        data={"username": "dudemcpants", "password": "an incorrect password",},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')

    messages = page.select(".flash-messages .red")
    assert len(messages) == 1
    assert messages[0].get_text(strip=True) == 'Unauthorized: bad credentials.'
