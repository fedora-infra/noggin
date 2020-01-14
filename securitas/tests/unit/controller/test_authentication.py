from bs4 import BeautifulSoup


def test_logout(client):
    """Test logout"""

    # check that when unauthed, we redirect back to /
    result = client.get('/logout', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'
