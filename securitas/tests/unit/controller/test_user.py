import python_freeipa
import mock
import pytest
from bs4 import BeautifulSoup
from flask import get_flashed_messages


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
    assert page.title.string == 'User: dummy - The Fedora Project'
    user_fullname = page.select("#user_fullname")
    assert len(user_fullname) == 1
    assert user_fullname[0].get_text(strip=True) == "Dummy User"


def test_user_unauthed(client):
    """Check that when unauthed, the user page redirects back to /."""
    result = client.get('/user/dudemcpants/')
    assert result.status_code == 302
    assert result.location == "http://localhost/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "Please log in to continue."
    assert category == "warning"


@pytest.mark.vcr()
def test_user_edit(client, logged_in_dummy_user):
    """Test getting the user edit page: /user/<username>/edit/"""
    result = client.get('/user/dummy/edit/')
    page = BeautifulSoup(result.data, 'html.parser')
    # print(page.prettify())
    assert page.title
    assert page.title.string == 'Edit User: dummy - The Fedora Project'
    form = page.select("form[action='/user/dummy/edit/']")
    assert len(form) == 1
    assert form[0].find("input", attrs={"name": "firstname"})["value"] == "Dummy"
    assert form[0].find("input", attrs={"name": "lastname"})["value"] == "User"
    assert form[0].find("input", attrs={"name": "mail"})["value"] == "dummy@example.com"
    assert (
        form[0].find("textarea", attrs={"name": "sshpubkeys-0"}).get_text(strip=True)
        == ""
    )


@pytest.mark.vcr()
def test_user_edit_post(client, logged_in_dummy_user):
    """Test posting to the user edit page: /user/<username>/edit/"""
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert result.status_code == 302
    assert result.location == f"http://localhost/user/dummy/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "Profile has been succesfully updated."
    assert category == "success"


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.vcr()
def test_user_edit_no_permission(method, client, logged_in_dummy_user):
    """Verify that a user can't be changed by another user."""
    result = client.open(
        "/user/dudemcpants/edit/",
        method=method,
        data=POST_CONTENTS if method == "POST" else None,
    )
    assert result.status_code == 302
    assert result.location == "http://localhost/user/dudemcpants/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "You do not have permission to edit this account."
    assert category == "danger"


@pytest.mark.vcr()
def test_user_edit_post_no_change(client, logged_in_dummy_user):
    """Test posting to the user edit page and making no change"""
    # Do it once
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert result.status_code == 302
    # Now do it again
    result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert result.status_code == 302
    messages = get_flashed_messages(with_categories=True)
    # There should be 2 messages because contratry to what the docs say, get_flashed_message does
    # not seem to remove messages from the stack when used here.
    assert len(messages) >= 1
    category, message = messages[-1]
    # Nothing changed, last message should be OK
    assert message == "Profile has been succesfully updated."
    assert category == "success"


@pytest.mark.vcr()
def test_user_edit_post_bad_request(client, logged_in_dummy_user):
    """Test handling of FreeIPA errors"""
    with mock.patch("securitas.security.ipa.Client.user_mod") as user_mod:
        user_mod.side_effect = python_freeipa.exceptions.BadRequest(
            message="something went wrong", code="4242"
        )
        result = client.post('/user/dummy/edit/', data=POST_CONTENTS)
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    error_message = page.select("#formerrors .text-danger")[0]
    assert error_message.string == 'something went wrong'
