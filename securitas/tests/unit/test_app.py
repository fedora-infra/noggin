from bs4 import BeautifulSoup


def test_root(client):
    """Test the root page"""

    result = client.get('/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'


def test_page_not_found(client):
    """Test the 404 error page"""

    result = client.get('/dudemcpants/')
    assert result.status_code == 404
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == '404: You\'ve ruined everything. - The Fedora Project'


def test_search_json(client):
    """Test the /search/json endpoint"""

    result = client.get('/search/json', follow_redirects=True)
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Self-Service Portal - The Fedora Project'
