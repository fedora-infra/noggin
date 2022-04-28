from unittest import mock

import pytest
from bs4 import BeautifulSoup
from flask import current_app

from noggin import __version__
from noggin.app import ipa_admin, talisman


@pytest.fixture
def nonfas_group(ipa_testing_config, app):
    ipa_admin.group_add(a_cn="nonfas-group")
    yield
    ipa_admin.group_del("nonfas-group")


@pytest.fixture
def nonfas_user(ipa_testing_config, app):
    ipa_admin.user_add(
        "nonfas-user",
        o_givenname="NonFAS",
        o_sn="User",
        o_cn="NonFAS User",
        o_mail="nonfas-user@unit.tests",
        o_userpassword="nonfas-user_password",
    )
    yield
    ipa_admin.user_del("nonfas-user")


@pytest.fixture
def client_with_https(client):
    current_app.debug = False
    talisman.force_https = True
    yield client
    talisman.force_https = False


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
    assert result.location == "/user/dummy/"


def test_root_registration_closed(client, mocker):
    """Test the root page when registration is closed"""
    mocker.patch.dict(current_app.config, {"REGISTRATION_OPEN": False})
    result = client.get('/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    register_tab = page.select_one("#register")
    alert = register_tab.select_one("div.alert-info")
    assert alert is not None
    assert alert.string.strip() == "Registration is closed at the moment."


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
        {'cn': 'Dummy User', 'uid': 'dummy', 'url': '/user/dummy/'},
        {
            'cn': 'dummy-group',
            'description': 'The dummy-group group',
            'url': '/group/dummy-group/',
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
    assert result.json == {"status": 200, "title": "OK"}
    assert result.data == b'{"status": 200, "title": "OK"}'


@pytest.mark.vcr()
def test_healthz_readiness_ok(client):
    """Test the /healthz/ready check endpoint"""
    result = client.get('/healthz/ready')
    assert result.status_code == 200
    assert result.json == {"status": 200, "title": "OK"}
    assert result.data == b'{"status": 200, "title": "OK"}'


@pytest.mark.vcr()
def test_healthz_readiness_not_ok(client):
    """Test the /healthz/ready check endpoint when not ready (IPA disabled)"""
    with mock.patch("noggin.app.ipa_admin.ping") as ipaping:
        ipaping.side_effect = Exception()
        result = client.get('/healthz/ready')
    assert result.status_code == 503
    assert result.json == {
        "status": 503,
        "title": "Can't connect to the FreeIPA Server",
    }
    assert (
        result.data
        == b'{"status": 503, "title": "Can\'t connect to the FreeIPA Server"}'
    )


@pytest.mark.vcr()
def test_healthz_no_https(client_with_https):
    """Test that the healthz endpoints don't require HTTPS"""
    # Make sure we force HTTPS on regular endpoints
    result = client_with_https.get('/')
    assert result.status_code == 302
    # The heathlz endpoints should not be redirected
    result = client_with_https.get('/healthz/live')
    assert result.status_code == 200
    result = client_with_https.get('/healthz/ready')
    assert result.status_code == 200


def test_version(client):
    """Test the version in the footer"""
    result = client.get('/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    powered_by = page.select_one("footer div div small")
    assert (
        powered_by.prettify()
        == """
<small>
 Powered by
 <a href="https://github.com/fedora-infra/noggin">
  noggin
 </a>
 v{}
</small>
""".strip().format(
            __version__
        )
    )


def test_version_openshift(mocker, client):
    """Test the version in the footer in openshift"""
    mocker.patch.dict(
        "noggin.controller.os.environ",
        {
            "OPENSHIFT_BUILD_REFERENCE": "tests",
            "OPENSHIFT_BUILD_COMMIT": "abcdef0123456789",
        },
    )
    result = client.get('/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    powered_by = page.select_one("footer div div small")
    assert (
        powered_by.prettify()
        == """
<small>
 Powered by
 <a href="https://github.com/fedora-infra/noggin">
  noggin
 </a>
 v{} (tests:abcdef0)
</small>
""".strip().format(
            __version__
        )
    )
