from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from fedora_messaging import testing as fml_testing

from noggin.app import ipa_admin
from noggin.representation.user import User
from noggin.tests.unit.utilities import (
    assert_form_generic_error,
    assert_redirects_with_flash,
)
from noggin_messages import UserUpdateV1


POST_CONTENTS = {
    "firstname": "Dummy",
    "lastname": "User",
    "mail": "dummy@example.com",
    "ircnick": "dummy,dummy_",
    "locale": "en-US",
    "timezone": "UTC",
    "github": "@dummy",
    "gitlab": "@dummy",
    "rhbz_mail": "dummy@example.com",
    "website_url": "http://example.org/dummy",
}

POST_CONTENTS_MIN = {
    "firstname": "Dummy",
    "lastname": "User",
    "mail": "dummy@example.com",
    "locale": "en-US",
    "timezone": "UTC",
}

POST_CONTENTS_KEYS = {
    "sshpubkeys-0": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCtX/SK86GrOa0xUadeZVbDXCj6wseamJQTpvjzNdKLgIBuQnA2dnR+jBS54rxUzHD1In/yI9r1VXr+KVZG4ULHmSuP3Icl0SUiVs+u+qeHP77Fa9rnQaxxCFL7uZgDSGSgMx0XtiQUrcumlD/9mrahCefU0BIKfS6e9chWwJnDnPSpyWf0y0NpaGYqPaV6Ukg2Z5tBvei6ghBb0e9Tusg9dHGvpv2B23dCzps6s5WBYY2TqjTHAEuRe6xR0agtPUE1AZ/DvSBKgwEz6RXIFOtv/fnZ0tERh238+n2nohMZNo1QAtQ6I0U9Kx2gdAgHRaMN6GzmbThji/MLgKlIJPSh"  # noqa: E501
}


@pytest.mark.vcr()
def test_user(client, logged_in_dummy_user):
    """Test the user detail page: /user/<username>/"""
    result = client.get('/user/dummy/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Profile for dummy - noggin'
    user_fullname = page.select("#user_fullname")
    assert len(user_fullname) == 1
    assert user_fullname[0].get_text(strip=True) == "Dummy User"


def test_user_unauthed(client):
    """Check that when unauthed, the user page redirects back to /."""
    result = client.get('/user/dudemcpants/')
    assert_redirects_with_flash(
        result,
        expected_url="/?next=/user/dudemcpants/%3F",
        expected_message="Please log in to continue.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_user_edit(client, logged_in_dummy_user):
    """Test getting the user edit page: /user/<username>/settings/profile/"""
    result = client.get('/user/dummy/settings/profile/')
    page = BeautifulSoup(result.data, 'html.parser')
    # print(page.prettify())
    assert page.title
    assert page.title.string == 'Settings for dummy - noggin'
    form = page.select("form[action='/user/dummy/settings/profile/']")
    assert len(form) == 1
    assert form[0].find("input", attrs={"name": "firstname"})["value"] == "Dummy"
    assert form[0].find("input", attrs={"name": "lastname"})["value"] == "User"
    assert form[0].find("input", attrs={"name": "mail"})["value"] == "dummy@example.com"
    """assert (
        form[0].find("textarea", attrs={"name": "sshpubkeys-0"}).get_text(strip=True)
        == ""
    )"""


@pytest.mark.vcr()
def test_user_edit_post(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/settings/profile/"""
    with fml_testing.mock_sends(
        UserUpdateV1(
            {
                "msg": {
                    "agent": "dummy",
                    "user": "dummy",
                    "fields": [
                        'timezone',
                        'locale',
                        'ircnick',
                        'github',
                        'gitlab',
                        'rhbz_mail',
                        'website_url',
                    ],
                }
            }
        )
    ):
        result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/profile/",
        expected_message="Profile Updated: <a href=\"/user/dummy/\">view your profile</a>",
        expected_category="success",
    )


@pytest.mark.vcr()
def test_user_edit_post_minimal_values(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/settings/profile/
        with the bare minimum of values """
    with fml_testing.mock_sends(
        UserUpdateV1(
            {
                "msg": {
                    "agent": "dummy",
                    "user": "dummy",
                    "fields": ['timezone', 'locale'],
                }
            }
        )
    ):
        result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS_MIN)
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/profile/",
        expected_message="Profile Updated: <a href=\"/user/dummy/\">view your profile</a>",
        expected_category="success",
    )


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.vcr()
def test_user_edit_no_permission(method, client, logged_in_dummy_user):
    """Verify that a user can't be changed by another user."""
    result = client.open(
        "/user/dudemcpants/settings/profile/",
        method=method,
        data=POST_CONTENTS if method == "POST" else None,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_edit_post_no_change(client, logged_in_dummy_user):
    """Test posting to the user edit page and making no change"""
    # Do it once
    with fml_testing.mock_sends(
        UserUpdateV1(
            {
                "msg": {
                    "agent": "dummy",
                    "user": "dummy",
                    "fields": [
                        'timezone',
                        'locale',
                        'ircnick',
                        'github',
                        'gitlab',
                        'rhbz_mail',
                        'website_url',
                    ],
                }
            }
        )
    ):
        result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)

    assert result.status_code == 302
    # Now do it again
    with fml_testing.mock_sends():
        result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)
    assert_form_generic_error(result, 'no modifications to be performed')


@pytest.mark.vcr()
def test_user_edit_post_bad_request(client, logged_in_dummy_user):
    """Test handling of FreeIPA errors"""
    with mock.patch("noggin.security.ipa.Client.user_mod") as user_mod:
        user_mod.side_effect = python_freeipa.exceptions.BadRequest(
            message="something went wrong", code="4242"
        )
        result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)
    assert_form_generic_error(result, 'something went wrong')


@pytest.mark.vcr()
def test_user_settings_keys(client, logged_in_dummy_user):
    """Test getting the user edit page: /user/<username>/settings/keys/"""
    result = client.get('/user/dummy/settings/keys/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Settings for dummy - noggin'
    form = page.select("form[action='/user/dummy/settings/keys/']")
    assert len(form) == 1
    assert (
        form[0].find("textarea", attrs={"name": "sshpubkeys-0"}).get_text(strip=True)
        == ""
    )


@pytest.mark.vcr()
def test_user_settings_keys_post(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/settings/keys/"""
    with fml_testing.mock_sends(
        UserUpdateV1(
            {"msg": {"agent": "dummy", "user": "dummy", "fields": ['sshpubkeys']}}
        )
    ):
        result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/keys/",
        expected_message="Profile Updated: <a href=\"/user/dummy/\">view your profile</a>",
        expected_category="success",
    )


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.vcr()
def test_user_settings_keys_no_permission(method, client, logged_in_dummy_user):
    """Verify that a user's keys can't be changed by another user."""
    result = client.open(
        "/user/dudemcpants/settings/keys/",
        method=method,
        data=POST_CONTENTS_KEYS if method == "POST" else None,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_keys_post_no_change(client, logged_in_dummy_user):
    """Test posting to the user edit page and making no change"""
    # Do it once
    with fml_testing.mock_sends(
        UserUpdateV1(
            {"msg": {"agent": "dummy", "user": "dummy", "fields": ['sshpubkeys']}}
        )
    ):
        result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)

    assert result.status_code == 302
    # Now do it again
    with fml_testing.mock_sends():
        result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)
    assert_form_generic_error(result, 'no modifications to be performed')


@pytest.mark.vcr()
def test_user_settings_keys_post_bad_request(client, logged_in_dummy_user):
    """Test handling of FreeIPA errors"""
    with mock.patch("noggin.security.ipa.Client.user_mod") as user_mod:
        user_mod.side_effect = python_freeipa.exceptions.BadRequest(
            message="something went wrong", code="4242"
        )
        result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)
    assert_form_generic_error(result, 'something went wrong')


@pytest.mark.vcr()
def test_user_settings_keys_post_whitespace(client, logged_in_dummy_user):
    """Test adding an SSH key with whitespace"""
    post_contents = POST_CONTENTS_KEYS.copy()
    post_contents["sshpubkeys-0"] = f" {post_contents['sshpubkeys-0']} \n "
    with fml_testing.mock_sends(
        UserUpdateV1(
            {"msg": {"agent": "dummy", "user": "dummy", "fields": ['sshpubkeys']}}
        )
    ):
        result = client.post('/user/dummy/settings/keys/', data=post_contents)
        assert_redirects_with_flash(
            result,
            expected_url="/user/dummy/settings/keys/",
            expected_message="Profile Updated: <a href=\"/user/dummy/\">view your profile</a>",
            expected_category="success",
        )
    user = User(ipa_admin.user_show("dummy")["result"])
    assert user.sshpubkeys == [POST_CONTENTS_KEYS["sshpubkeys-0"]]


@pytest.mark.vcr()
def test_user_cant_see_hidden_groups(client, logged_in_dummy_user):
    result = client.get('/user/dummy/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Profile for dummy - noggin'
    assert (
        page.select_one('.list-group-item.h4').get_text(strip=True)
        == 'dummy has no group memberships'
    )


@pytest.mark.vcr()
def test_user_can_see_dummy_group(client, dummy_user_as_group_manager):
    result = client.get('/user/dummy/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Profile for dummy - noggin'
    assert (
        page.select_one('.list-group-item.text-right.bg-light strong').get_text(
            strip=True
        )
        == '1 Group Memberships'
    )


@pytest.mark.vcr()
def test_user_with_indirect_groups(
    client, logged_in_dummy_user, dummy_group, make_group
):
    make_group("parent-group")
    ipa_admin.group_add_member("parent-group", o_group="dummy-group")
    ipa_admin.group_add_member("dummy-group", o_user="dummy")
    result = client.get('/user/dummy/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert (
        page.select_one('.list-group-item.text-right.bg-light strong').get_text(
            strip=True
        )
        == '2 Group Memberships'
    )
    assert len(page.select('.list-group .list-group-item span.title')) == 2


@pytest.mark.vcr()
def test_user_with_no_groups(client, logged_in_dummy_user, dummy_group):
    ipa_admin.group_remove_member("ipausers", o_user="dummy")
    result = client.get('/user/dummy/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert (
        page.select_one('.list-group-item.h4').get_text(strip=True)
        == 'dummy has no group memberships'
    )


@pytest.mark.vcr()
def test_user_settings_agreements(client, logged_in_dummy_user, dummy_agreement):
    """Test getting the user agreements page: /user/<username>/settings/agreements/"""
    result = client.get('/user/dummy/settings/agreements/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert len(page.select("#agreement-modal-dummyagreement")) == 1


@pytest.mark.vcr()
def test_user_settings_agreements_disabled(
    client, logged_in_dummy_user, dummy_agreement
):
    """Test getting the user agreements page: /user/<username>/settings/agreements/"""
    ipa_admin.fasagreement_disable("dummy agreement")
    result = client.get('/user/dummy/settings/agreements/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert len(page.select("#agreement-modal-dummyagreement")) == 0


@pytest.mark.vcr()
def test_user_settings_agreements_post(client, logged_in_dummy_user, dummy_agreement):
    """Test signing an agreement"""
    result = client.post(
        '/user/dummy/settings/agreements/', data={"agreement": "dummy agreement"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/agreements/",
        expected_message="You signed the \"dummy agreement\" agreement.",
        expected_category="success",
    )


@pytest.mark.vcr()
def test_user_settings_agreements_post_bad_request(
    client, logged_in_dummy_user, dummy_agreement
):
    """Test handling of FreeIPA errors"""
    with mock.patch(
        "noggin.security.ipa.Client.fasagreement_add_user"
    ) as fasagreement_add_user:
        fasagreement_add_user.side_effect = python_freeipa.exceptions.BadRequest(
            message="something went wrong", code="4242"
        )
        result = client.post(
            '/user/dummy/settings/agreements/', data={"agreement": "dummy agreement"}
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/agreements/",
        expected_message="Cannot sign the agreement \"dummy agreement\": something went wrong",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_agreements_post_unknown(
    client, logged_in_dummy_user, dummy_agreement
):
    """Test signing an unknown agreement"""
    result = client.post(
        '/user/dummy/settings/agreements/', data={"agreement": "this does not exist"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/agreements/",
        expected_message="Unknown agreement: this does not exist.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_user_private(client, logged_in_dummy_user, make_user):
    """A user with fasIsPrivate should be anonymized as much as possible."""
    make_user("testuser")
    ipa_admin.user_mod("testuser", fasisprivate=True)
    result = client.get('/user/testuser/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    # print(page.prettify())
    user_fullname = page.select_one("#user_fullname")
    assert user_fullname is not None
    assert user_fullname.get_text(strip=True) == "testuser"
    user_attributes = page.select_one("ul#user_attributes")
    assert user_attributes is not None
    assert len(user_attributes.find_all("li")) == 0
