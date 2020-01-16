from bs4 import BeautifulSoup


def test_user(client):
    """Test the user detail page: /user/<username>/"""

    # check that when unauthed, we redirect back to /
    result = client.get('/user/dudemcpants', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'


def test_user_edit(client):
    """Test the user edit page: /user/<username>/edit/"""

    # check that when unauthed, we redirect back to /
    result = client.get('/user/dudemcpants/edit/', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'
