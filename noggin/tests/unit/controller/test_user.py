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
    """Test getting the user edit page: /user/<username>/settings/profile/"""
    result = client.get('/user/dummy/settings/profile/')
    page = BeautifulSoup(result.data, 'html.parser')
    # print(page.prettify())
    assert page.title
    assert page.title.string == 'dummy\'s Settings - noggin'
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
    result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)
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
    result = client.post('/user/dummy/settings/profile/', data=POST_CONTENTS)

    assert result.status_code == 302
    # Now do it again
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
    assert page.title.string == 'dummy\'s Settings - noggin'
    form = page.select("form[action='/user/dummy/settings/keys/']")
    assert len(form) == 1
    assert (
        form[0].find("textarea", attrs={"name": "sshpubkeys-0"}).get_text(strip=True)
        == ""
    )


@pytest.mark.vcr()
def test_user_settings_keys_post(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/settings/keys/"""
    result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/",
        expected_message="Profile has been succesfully updated.",
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
    result = client.post('/user/dummy/settings/keys/', data=POST_CONTENTS_KEYS)

    assert result.status_code == 302
    # Now do it again
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
def test_user_settings_otp(client, logged_in_dummy_user):
    """Test getting the user OTP settings page: /user/<username>/settings/otp/"""
    result = client.get('/user/dummy/settings/otp/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'dummy\'s Settings - noggin'
    # check the pageheading
    pageheading = page.select("#pageheading")[0]
    assert pageheading.get_text(strip=True) == "OTP Tokens"
    # check that there arent any tokens
    tokenlist = page.select("div.list-group")
    assert len(tokenlist) == 1
    assert (
        tokenlist[0].select(".list-group-item")[0].get_text(strip=True)
        == "You have no OTP tokens"
    )
    # we shouldnt see a form, because there is no GPGkey
    form = page.select("form[action='/user/dummy/settings/otp/add/']")
    assert len(form) == 0

    # add a GPG key
    client.post('/user/dummy/settings/keys/', data={"gpgkeys-0": "fcd8ae3e6005d76a"})

    result = client.get('/user/dummy/settings/otp/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'dummy\'s Settings - noggin'
    # now with a GPG key, we should see the form.
    form = page.select("form[action='/user/dummy/settings/otp/add/']")
    assert len(form) == 1


@pytest.mark.vcr()
def test_user_settings_otp_no_permission(client, logged_in_dummy_user):
    """Verify that a user's OTP settings page can't be viewed by another user."""
    result = client.get("/user/dudemcpants/settings/otp/")
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_add(client, logged_in_dummy_user):
    """Test posting to the create OTP endpoint"""
    # first, add a GPG key
    client.post('/user/dummy/settings/keys/', data={"gpgkeys-0": "fcd8ae3e6005d76a"})

    result = client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants token"},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, 'html.parser')
    tokenlist = page.select("div.list-group")
    assert len(tokenlist) == 1

    # check the token is in the list
    assert (
        tokenlist[0].select(".list-group-item .h6")[0].get_text(strip=True)
        == "pants token"
    )

    # check the modal is on the page
    assert len(page.select("#otpModal")) == 1


@pytest.mark.vcr()
def test_user_settings_otp_add_nogpg(client, logged_in_dummy_user):
    """Test trying to make an otp token without a gpgkey"""
    result = client.post(
        '/user/dummy/settings/otp/add/', data={"description": "pants token"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot create an OTP token without a GPG Key. Please add a GPG Key",
        expected_category="info",
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't make an otp token. """
    result = client.post(
        "/user/dudemcpants/settings/otp/add/", data={"description": "pants token"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_invalid_form(client, logged_in_dummy_user):
    """Test an invalid form when adding an otp token"""
    client.post(
        '/user/dummy/settings/keys/',
        data={"gpgkeys-0": "fcd8ae3e6005d76a"},
        follow_redirects=True,
    )
    result = client.post('/user/dummy/settings/otp/add/', data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Description must not be empty",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_invalid(client, logged_in_dummy_user):
    """Test failure when adding an otptoken"""
    client.post(
        '/user/dummy/settings/keys/',
        data={"gpgkeys-0": "fcd8ae3e6005d76a"},
        follow_redirects=True,
    )
    with mock.patch("noggin.security.ipa.Client.otptoken_add") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            '/user/dummy/settings/otp/add/', data={"description": "pants token"}
        )

    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot create the token.",
        expected_category="danger",
    )

@pytest.mark.vcr()
def test_user_settings_otp_disable_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't disable an otp token. """
    result = client.post(
        "/user/dudemcpants/settings/otp/disable/", data={"description": "pants token"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_disable_invalid_form(client, logged_in_dummy_user):
    """Test an invalid form when disabling an otp token"""
    result = client.post('/user/dummy/settings/otp/disable/', data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="token must not be empty",
        expected_category="danger",
    )

@pytest.mark.vcr()
def test_user_settings_otp_disable(client, logged_in_dummy_user):
    """Test failure when disabling an otptoken"""
    client.post('/user/dummy/settings/keys/', data={"gpgkeys-0": "fcd8ae3e6005d76a"})

    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants token"},
        follow_redirects=True,
    )
    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants' other token"},
        follow_redirects=True,
    )
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Cannot disable the token.",
            code="4242",
        )
        result = client.post(
            '/user/dummy/settings/otp/disable/',
            data={"token": "0be795bd-b7d3-49b2-89d7-889522d7f1ba"}
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot disable the token.",
        expected_category="danger",
    )

@pytest.mark.vcr()
def test_user_settings_otp_disable_last_active(client, logged_in_dummy_user):
    """Test failure when disabling the last remaining active otptoken"""
    client.post('/user/dummy/settings/keys/', data={"gpgkeys-0": "fcd8ae3e6005d76a"})

    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants token"},
        follow_redirects=True,
    )
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Unable to disable last active token.",
            code="4242",
        )
        result = client.post(
            '/user/dummy/settings/otp/disable/',
            data={"token": "0be795bd-b7d3-49b2-89d7-889522d7f1ba"}
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Unable to disable last active token.",
        expected_category="danger",
    )

@pytest.mark.vcr()
def test_user_settings_otp_disable_with_multiple(client, logged_in_dummy_user):
    """Test failure when disabling the last remaining active otptoken"""
    client.post('/user/dummy/settings/keys/', data={"gpgkeys-0": "fcd8ae3e6005d76a"})

    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants token"},
    )
    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants other token"},
    )
    client.post(
        '/user/dummy/settings/otp/add/',
        data={"description": "pants other other token"},
        follow_redirects=True,
    )

    fetch = client.get(
        '/user/dummy/settings/otp/'
    )

    page = BeautifulSoup(fetch.data, 'html.parser')
    tokenlist = page.select("div.list-group")

    id = (tokenlist[0].select(".list-group-item")[0]
          .select(".text-monospace")[0].get_text(strip=True))
    result = client.post(
        '/user/dummy/settings/otp/disable/',
        data={"token": id},
        follow_redirects=True
    )

    id = (tokenlist[0].select(".list-group-item")[2]
          .select(".text-monospace")[0].get_text(strip=True))
    result = client.post(
        '/user/dummy/settings/otp/disable/',
        data={"token": id},
        follow_redirects=True
    )

    fetch = client.get(
        '/user/dummy/settings/otp/'
    )

    page = BeautifulSoup(fetch.data, 'html.parser')
    tokenlist = page.select("div.list-group")

    assert (
        "disabled" in tokenlist[0].select("div.list-group-item")[0].get_text(strip=True)
    )

    assert result.status_code == 200

