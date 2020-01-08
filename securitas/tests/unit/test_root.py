from bs4 import BeautifulSoup


def test_root(client):
    """Test the root page"""

    result = client.get('/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'
