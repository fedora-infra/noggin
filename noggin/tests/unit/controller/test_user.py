import python_freeipa
import mock
import pytest
from bs4 import BeautifulSoup

from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_generic_error,
)


POST_CONTENTS = {
    "firstname": "Dummy",
    "lastname": "User",
    "mail": "dummy@example.com",
    "ircnick": "dummy",
    "locale": "en-US",
    "timezone": "UTC",
    "github": "@dummy",
    "gitlab": "@dummy",
    "rhbz_mail": "dummy@example.com",
    "sshpubkeys-0": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCtX/SK86GrOa0xUadeZVbDXCj6wseamJQTpvjzNdKLgIBuQnA2dnR+jBS54rxUzHD1In/yI9r1VXr+KVZG4ULHmSuP3Icl0SUiVs+u+qeHP77Fa9rnQaxxCFL7uZgDSGSgMx0XtiQUrcumlD/9mrahCefU0BIKfS6e9chWwJnDnPSpyWf0y0NpaGYqPaV6Ukg2Z5tBvei6ghBb0e9Tusg9dHGvpv2B23dCzps6s5WBYY2TqjTHAEuRe6xR0agtPUE1AZ/DvSBKgwEz6RXIFOtv/fnZ0tERh238+n2nohMZNo1QAtQ6I0U9Kx2gdAgHRaMN6GzmbThji/MLgKlIJPSh",  # noqa: E501
}


@pytest.mark.vcr()
def test_user(client, logged_in_dummy_user):
    """Test the user detail page: /user/<username>/"""
    result = client.get('/user/dummy/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'dummy\'s Profile - noggin'
    user_fullname = page.select("#user_fullname")
    assert len(user_fullname) == 1
    assert user_fullname[0].get_text(strip=True) == "Dummy User"


def test_user_unauthed(client):
    """Check that when unauthed, the user page redirects back to /."""
    result = client.get('/user/dudemcpants/')
    assert_redirects_with_flash(
        result,
        expected_url="/",
        expected_message="Please log in to continue.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_user_edit(client, logged_in_dummy_user):
    """Test getting the user edit page: /user/<username>/edit/"""
    result = client.get('/user/dummy/edit/')
    page = BeautifulSoup(result.data, 'html.parser')
    # print(page.prettify())
    assert page.title
    assert page.title.string == 'dummy\'s Settings - noggin'
    form = page.select("form[action='/user/dummy/edit/']")
    assert len(form) == 2
    assert form[0].find("input", attrs={"name": "firstname"})["value"] == "Dummy"
    assert form[0].find("input", attrs={"name": "lastname"})["value"] == "User"
    assert form[1].find("input", attrs={"name": "mail"})["value"] == "dummy@example.com"
    assert (
        form[0].find("textarea", attrs={"name": "sshpubkeys-0"}).get_text(strip=True)
        == ""
    )


@pytest.mark.vcr()
def test_user_edit_post(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/edit/"""
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/",
        expected_message="Profile has been succesfully updated.",
        expected_category="success",
    )


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.vcr()
def test_user_edit_no_permission(method, client, logged_in_dummy_user):
    """Verify that a user can't be changed by another user."""
    result = client.open(
        "/user/dudemcpants/edit/",
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
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert result.status_code == 302
    # Now do it again
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert_form_generic_error(result, 'no modifications to be performed')


@pytest.mark.vcr()
def test_user_edit_post_bad_request(client, logged_in_dummy_user):
    """Test handling of FreeIPA errors"""
    with mock.patch("noggin.security.ipa.Client.user_mod") as user_mod:
        user_mod.side_effect = python_freeipa.exceptions.BadRequest(
            message="something went wrong", code="4242"
        )
        result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert_form_generic_error(result, 'something went wrong')
