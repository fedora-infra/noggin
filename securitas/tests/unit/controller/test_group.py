from bs4 import BeautifulSoup


def test_group(client):
    """Test the group detail page: /group/<groupname>"""

    # check that when unauthed, we redirect back to /
    result = client.get('/group/fedora-design', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'


def test_groups(client):
    """Test the groups list: /groups/"""

    # check that when unauthed, we redirect back to /
    result = client.get('/groups/', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'
