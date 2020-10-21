from unittest import mock

import pytest
from bs4 import BeautifulSoup

from noggin.app import ipa_admin

from .. import tweak_app_config


@pytest.fixture
def nonfas_group(ipa_testing_config, app):
    ipa_admin.group_add(a_cn="nonfas-group")
    yield
    ipa_admin.group_del("nonfas-group")


@pytest.fixture
def nonfas_user(ipa_testing_config, app):
    ipa_admin.user_add(
        a_uid="nonfas-user",
        o_givenname="NonFAS",
        o_sn="User",
        o_cn="NonFAS User",
        o_mail="nonfas-user@example.com",
        o_userpassword="nonfas-user_password",
    )
    yield
    ipa_admin.user_del("nonfas-user")


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
@pytest.mark.parametrize("app_root", (None, "/accounts/"))
def test_search_json(app, client, logged_in_dummy_user, dummy_group, app_root):
    """Test the /search/json endpoint"""

    if app_root:
        addl_config = {"APPLICATION_ROOT": app_root}
    else:
        addl_config = {}
        app_root = "/"

    with tweak_app_config(app, addl_config):
        result = client.get('/search/json?username=dummy&group=dummy-group')
        assert result.status_code == 200
        assert result.json == [
            {
                'cn': 'Dummy User',
                'uid': 'dummy',
                'url': f'http://localhost{app_root}user/dummy/',
            },
            {
                'cn': 'dummy-group',
                'description': 'A dummy group',
                'url': f'http://localhost{app_root}group/dummy-group/',
            },
        ]


@pytest.mark.vcr()
def test_search_json_empty(client, logged_in_dummy_user):
    """Test the /search/json endpoint with an empty search"""
    result = client.get('/search/json')
    assert result.status_code == 200
    assert result.json == []


@pytest.mark.vcr()
def test_search_json_user_nonfas(client, logged_in_dummy_user, nonfas_user):
    """The /search/json endpoint should only return FAS users"""
    result = client.get('/search/json?user=nonfas')
    assert result.status_code == 200
    assert result.json == []


@pytest.mark.vcr()
def test_search_json_group_nonfas(client, logged_in_dummy_user, nonfas_group):
    """The /search/json endpoint should only return FAS groups"""
    result = client.get('/search/json?group=nonfas')
    assert result.status_code == 200
    assert result.json == []


@pytest.mark.vcr()
def test_healthz_liveness(client):
    """Test the /healthz/live check endpoint"""
    result = client.get('/healthz/live')
    assert result.status_code == 200
    assert result.data == b'OK\n'


@pytest.mark.vcr()
def test_healthz_readiness_ok(client):
    """Test the /healthz/ready check endpoint"""
    result = client.get('/healthz/ready')
    assert result.status_code == 200
    assert result.data == b'OK\n'


@pytest.mark.vcr()
def test_healthz_readiness_not_ok(client):
    """Test the /healthz/ready check endpoint when not ready (IPA disabled)"""
    with mock.patch("noggin.app.ipa_admin.ping") as ipaping:
        ipaping.side_effect = Exception()
        result = client.get('/healthz/ready')
    assert result.status_code == 503
    assert result.data == b"Can't connect to the FreeIPA Server\n"
