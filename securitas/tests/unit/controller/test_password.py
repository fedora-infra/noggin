from bs4 import BeautifulSoup


def test_password_reset(client):
    """Test the password reset page"""

    # check that when unauthed, we redirect back to /
    result = client.get('/password-reset')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Password Reset - The Fedora Project'
