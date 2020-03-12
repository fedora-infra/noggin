import pytest
from bs4 import BeautifulSoup


def test_root(client):
    """Test the root page"""
    result = client.get('/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'noggin'


@pytest.mark.vcr()
def test_root_authenticated(client, logged_in_dummy_user):
    """Test the root page when the user is authenticated"""
    result = client.get('/')
    assert result.status_code == 302
    assert result.location == "http://localhost/user/dummy/"


def test_page_not_found(client):
    """Test the 404 error page"""
    result = client.get('/dudemcpants/')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_search_json(client, logged_in_dummy_user, dummy_group):
    """Test the /search/json endpoint"""
    result = client.get('/search/json?username=dummy&group=dummy-group')
    assert result.status_code == 200
    assert result.json == [
        {'cn': 'Dummy User', 'uid': 'dummy'},
        {'cn': 'dummy-group', 'description': 'A dummy group'},
    ]


@pytest.mark.vcr()
def test_search_json_empty(client, logged_in_dummy_user):
    """Test the /search/json endpoint with an empty search"""
    result = client.get('/search/json')
    assert result.status_code == 200
    assert result.json == []
