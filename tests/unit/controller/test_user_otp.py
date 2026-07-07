from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import get_flashed_messages
from pyotp import TOTP

from noggin.app import ipa_admin
from noggin.representation.otptoken import OTPToken

from ..utilities import (
    assert_form_field_error,
    assert_form_generic_error,
    assert_redirects_with_flash,
    get_otp,
    otp_secret_from_uri,
)


@pytest.fixture
def dummy_user_with_2_otp(client, logged_in_dummy_user, logged_in_dummy_user_with_otp):
    ipa = logged_in_dummy_user
    result = ipa.otptoken_add(
        o_ipatokenowner="dummy",
        o_description="dummy's other token",
    )['result']
    token = OTPToken(result)
    yield logged_in_dummy_user_with_otp, token
    try:
        ipa_admin.otptoken_del(token.uniqueid)
    except python_freeipa.exceptions.NotFound:
        pass  # already deleted, it's fine.


@pytest.fixture
def totp_token():
    return TOTP("BJ3F2NQ2CADX6ZOEDGGKATDQMVTKY3XLC73ASUHIBVGGGWJJOYFXIFIT")


@pytest.mark.vcr()
def test_user_settings_otp(client, logged_in_dummy_user):
    """Test getting the user OTP settings page: /user/<username>/settings/otp/"""
    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    assert page.title
    assert page.title.string == "Settings for dummy - noggin"
    # check the pageheading
    pageheading = page.select("#pageheading")[0]
    assert pageheading.get_text(strip=True) == "OTP Tokens"
    # check that there arent any tokens
    tokenlist = page.select("div.list-group")
    assert len(tokenlist) == 1
    assert (
        tokenlist[0].select(".list-group-item")[0].get_text(strip=True)
        == "You have no OTP tokensAdd an OTP token to enable two-factor "
        "authentication on your account."
    )

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    assert page.title
    assert page.title.string == "Settings for dummy - noggin"

    form = page.select("form[action='/user/dummy/settings/otp/']")
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
def test_user_settings_otp_add(client, logged_in_dummy_user, cleanup_dummy_tokens):
    """Test the first step of OTP creation"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "add-description": "pants token",
            "add-password": "dummy_password",
            "add-submit": "1",
        },
    )
    page = BeautifulSoup(result.data, "html.parser")
    # The token has not been added yet
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    assert "You have no OTP tokens" in tokenlist.get_text(strip=True)
    # check the modal is on the page
    modal = page.select_one("#otp-modal")
    assert modal is not None
    # check the next step form is properly pre-filled
    confirm_form = modal.select_one("form")
    assert confirm_form is not None
    assert (
        confirm_form.select_one("input[name='confirm-description']")["value"]
        == "pants token"
    )
    otp_uri = page.select_one("input#otp-uri")
    parsed_otp_uri_query = parse_qs(urlparse(otp_uri["value"]).query)
    assert (
        confirm_form.select_one("input[name='confirm-secret']")["value"]
        == parsed_otp_uri_query["secret"][0]
    )


@pytest.mark.vcr()
def test_user_settings_otp_confirm(
    client, logged_in_dummy_user, cleanup_dummy_tokens, totp_token
):
    """Test OTP creation"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "confirm-description": "pants token",
            "confirm-secret": totp_token.secret,
            "confirm-code": totp_token.now(),
            "confirm-submit": "1",
        },
    )
    assert result.status_code == 302
    assert result.location == "/user/dummy/settings/otp/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 2
    assert messages[0] == ("success", "The token has been created.")
    assert messages[1][0] == "warning"
    assert "recovery codes" in messages[1][1].lower()
    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    # check this is not the no tokens message
    assert "You have no OTP tokens" not in tokenlist.get_text(strip=True)
    # check we are showing 1 token
    tokens = tokenlist.select(".list-group-item .col")
    assert len(tokens) == 1
    # check the token is in the list
    description = tokens[0].select_one("div[data-role='token-description']")
    assert description is not None
    assert description.get_text(strip=True) == "pants token"
    # check the modal is closed
    assert page.select_one("#otp-modal") is None


@pytest.mark.vcr()
def test_user_settings_otp_add_second(
    client, logged_in_dummy_user_with_otp, cleanup_dummy_tokens
):
    """Test posting to the create OTP endpoint"""
    otp = get_otp(otp_secret_from_uri(logged_in_dummy_user_with_otp.uri))
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "add-description": "pants token 2",
            "add-password": "dummy_password",
            "add-otp": otp,
            "add-submit": "1",
        },
    )
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    tokens = tokenlist.select(".list-group-item div[data-role='token-description']")
    assert len(tokens) == 1

    modal = page.select_one("#otp-modal")
    assert modal is not None

    confirm_form = modal.select_one("form")
    assert confirm_form is not None
    assert (
        confirm_form.select_one("input[name='confirm-description']")["value"]
        == "pants token 2"
    )
    otp_uri = page.select_one("input#otp-uri")
    parsed_otp_uri_query = parse_qs(urlparse(otp_uri["value"]).query)
    assert (
        confirm_form.select_one("input[name='confirm-secret']")["value"]
        == parsed_otp_uri_query["secret"][0]
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_second_confirm(
    client,
    logged_in_dummy_user_with_otp,
    cleanup_dummy_tokens,
    totp_token,
):
    """Test posting to the create OTP endpoint"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "confirm-description": "pants token",
            "confirm-secret": totp_token.secret,
            "confirm-code": totp_token.now(),
            "confirm-submit": "1",
        },
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    # check we are showing 2 tokens
    tokens = tokenlist.select(".list-group-item div[data-role='token-description']")
    assert len(tokens) == 2
    # check the 2nd token is in the list
    assert tokens[1].get_text(strip=True) == "pants token"
    # check the modal is closed
    assert page.select_one("#otp-modal") is None


@pytest.mark.vcr()
def test_user_settings_otp_check_no_description(
    client, logged_in_dummy_user, cleanup_dummy_tokens, totp_token
):
    """Test an OTP token without a description"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "confirm-secret": totp_token.secret,
            "confirm-code": totp_token.now(),
            "confirm-submit": "1",
        },
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")

    assert tokenlist is not None

    tokens = tokenlist.select(".list-group-item div[data-role='token-description']")
    assert len(tokens) == 1

    assert tokens[0].get_text(strip=True) == "(no name)"


@pytest.mark.vcr()
def test_user_settings_otp_check_description_escaping(
    client, logged_in_dummy_user, cleanup_dummy_tokens
):
    """Test that we escape the token description when constructing the OTP URI"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "add-description": "pants token",
            "add-password": "dummy_password",
            "add-submit": "1",
        },
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    otp_uri = page.select_one("input#otp-uri")
    assert otp_uri is not None
    parsed_otp_uri = urlparse(otp_uri["value"])

    # Not sure we need all of these checked
    assert parsed_otp_uri.scheme == "otpauth"
    assert parsed_otp_uri.netloc == "totp"
    assert parsed_otp_uri.path == "/dummy%40TINYSTAGE.TEST:pants%20token"

    parsed_query = parse_qs(parsed_otp_uri.query)
    assert parsed_query["issuer"] == ["dummy@TINYSTAGE.TEST"]


@pytest.mark.vcr()
def test_user_settings_otp_add_no_permission(client, logged_in_dummy_user, totp_token):
    """Verify that another user can't make an otp token."""
    result = client.post(
        "/user/dudemcpants/settings/otp/",
        data={
            "confirm-description": "pants token",
            "confirm-secret": totp_token.secret,
            "confirm-code": totp_token.now(),
            "confirm-submit": "1",
        },
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
    result = client.post("/user/dummy/settings/otp/", data={"add-submit": "1"})
    assert_form_field_error(result, "add-password", "You must provide a password")


@pytest.mark.vcr()
def test_user_settings_otp_add_wrong_password(client, logged_in_dummy_user):
    """Test adding an otp token with the wrong password"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "add-description": "pants token",
            "add-password": "pants",
            "add-submit": "1",
        },
    )
    assert_form_field_error(result, "add-password", "Incorrect password")


@pytest.mark.vcr()
def test_user_settings_otp_add_wrong_code(client, logged_in_dummy_user, totp_token):
    """Test failure when adding an otptoken"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={
            "confirm-description": "pants token",
            "confirm-secret": totp_token.secret,
            "confirm-code": "123456",
            "confirm-submit": "1",
        },
    )
    assert_form_field_error(
        result, "confirm-code", "The code is wrong, please try again."
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_invalid(client, logged_in_dummy_user, totp_token):
    """Test failure when adding an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_add") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            "/user/dummy/settings/otp/",
            data={
                "confirm-description": "pants token",
                "confirm-secret": totp_token.secret,
                "confirm-code": totp_token.now(),
                "confirm-submit": "1",
            },
        )
    assert_form_generic_error(result, expected_message="Cannot create the token.")


@pytest.mark.vcr()
def test_user_settings_otp_disable_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't disable an otp token."""
    result = client.post(
        "/user/dudemcpants/settings/otp/disable/",
        data={"description": "pants token", "password": "dummy_password"},
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
    result = client.post("/user/dummy/settings/otp/disable/", data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Token must not be empty",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_disable_ipaerror(
    client, logged_in_dummy_user, dummy_user_with_2_otp
):
    """Test failure when disabling an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Cannot disable the token.", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/disable/",
            data={"token": dummy_user_with_2_otp[1].uniqueid},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot disable the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_disable(client, logged_in_dummy_user, dummy_user_with_2_otp):
    """Test deleting an otptoken"""
    # add another OTP Token
    result = client.get("/user/dummy/settings/otp/")

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are showing 2 tokens
    assert len(tokenlist) == 2

    # grab the id of the first token
    tokenid = tokenlist[0].select(".text-monospace")[0].get_text(strip=True)

    # disable that token
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": tokenid},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are still showing 2 item
    assert len(tokenlist) == 2


@pytest.mark.vcr()
def test_user_settings_otp_disable_lasttoken(client, logged_in_dummy_user_with_otp):
    """Test trying to disable the last token"""
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": logged_in_dummy_user_with_otp.uniqueid},
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Sorry, You cannot disable your last active token.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_user_settings_otp_disable_ipabadrequest(
    client, logged_in_dummy_user, dummy_user_with_2_otp
):
    """Test IPA badrequest failure when disabling an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.BadRequest(
            message="Cannot delete the token.", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/disable/",
            data={"token": "0be795bd-b7d3-49b2-89d7-889522d7f1ba"},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot disable the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_delete_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't delete an otp token."""
    result = client.post(
        "/user/dudemcpants/settings/otp/delete/", data={"token": "aabbcc-aabbcc"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_delete_invalid_form(client, logged_in_dummy_user):
    """Test an invalid form when deleting an otp token"""
    result = client.post("/user/dummy/settings/otp/delete/", data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Token must not be empty",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_delete_ipafailure(
    client, logged_in_dummy_user, dummy_user_with_2_otp
):
    """Test IPA failure when deleting an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_del") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Cannot delete the token.", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/delete/",
            data={"token": "0be795bd-b7d3-49b2-89d7-889522d7f1ba"},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot delete the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_delete_ipabadrequest(
    client, logged_in_dummy_user, dummy_user_with_2_otp
):
    """Test IPA badrequest failure when deleting an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_del") as method:
        method.side_effect = python_freeipa.exceptions.BadRequest(
            message="Cannot delete the token.", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/delete/",
            data={"token": "0be795bd-b7d3-49b2-89d7-889522d7f1ba"},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot delete the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_delete(client, logged_in_dummy_user, dummy_user_with_2_otp):
    """Test deleting an otptoken"""
    result = client.get("/user/dummy/settings/otp/")

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are showing 2 tokens
    assert len(tokenlist) == 2

    # grab the id of the first token
    tokenid = tokenlist[0].select(".text-monospace")[0].get_text(strip=True)

    # delete that token
    result = client.post(
        "/user/dummy/settings/otp/delete/",
        data={"token": tokenid},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are showing 1 item
    assert len(tokenlist) == 1

    # check the one item is not the no tokens message
    assert "You have no OTP tokens" not in tokenlist[0].get_text(strip=True)


@pytest.mark.vcr()
def test_user_settings_otp_delete_lasttoken(
    client, logged_in_dummy_user, logged_in_dummy_user_with_otp
):
    """Test trying to delete the last token"""
    result = client.get("/user/dummy/settings/otp/")

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are showing 1 token
    assert len(tokenlist) == 1

    # check the one item is not the no tokens message
    assert "You have no OTP tokens" not in tokenlist[0].get_text(strip=True)

    # grab the id of the token
    tokenid = tokenlist[0].select(".text-monospace")[0].get_text(strip=True)

    # try to delete that token
    result = client.post("/user/dummy/settings/otp/delete/", data={"token": tokenid})

    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Sorry, You cannot delete your last active token.",
        expected_category="warning",
    )


@pytest.mark.vcr()
def test_user_settings_otp_enable_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't enable an otp token."""
    result = client.post(
        "/user/dudemcpants/settings/otp/enable/",
        data={"description": "pants token", "password": "dummy_password"},
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_enable_invalid_form(client, logged_in_dummy_user):
    """Test an invalid form when enabling an otp token"""
    result = client.post("/user/dummy/settings/otp/enable/", data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Token must not be empty",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_enable_ipaerror(
    client, logged_in_dummy_user, dummy_user_with_2_otp
):
    """Test failure when enabling an otptoken"""
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Cannot enable the token.", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/enable/",
            data={"token": dummy_user_with_2_otp[1].uniqueid},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot enable the token. Cannot enable the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_enable(client, logged_in_dummy_user, dummy_user_with_2_otp):
    """Test enabling an otptoken"""
    # add another OTP Token
    result = client.get("/user/dummy/settings/otp/")

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")

    # check we are showing 2 tokens
    assert len(tokenlist) == 2

    # grab the id of the first token
    tokenid = tokenlist[0].select(".text-monospace")[0].get_text(strip=True)

    # disable that token
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": tokenid},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")

    # select all the tokens, disabled and enabled
    tokenlist = page.select("div.list-group .list-group-item")
    # check we are showing 2 tokens
    assert len(tokenlist) == 2

    # select just the disabled tokens
    tokenlist = page.select("div.list-group .list-group-item.text-muted")
    # check we are showing 1 disabled item
    assert len(tokenlist) == 1

    # enable that token
    result = client.post(
        "/user/dummy/settings/otp/enable/",
        data={"token": tokenid},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")

    # select all the tokens, disabled and enabled
    tokenlist = page.select("div.list-group .list-group-item")
    # check we are showing 2 tokens
    assert len(tokenlist) == 2

    # try to select just the disabled tokens
    tokenlist = page.select("div.list-group .list-group-item.text-muted")
    # check we are showing 0 disabled tokens
    assert len(tokenlist) == 0


@pytest.mark.vcr()
def test_user_settings_otp_rename(client, logged_in_dummy_user_with_otp):
    """Test renaming an otp token"""
    tokenid = logged_in_dummy_user_with_otp.uniqueid
    # rename the token
    result = client.post(
        "/user/dummy/settings/otp/rename/",
        data={"token": tokenid, "description": "the new name"},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")
    assert len(tokenlist) == 1

    desc = (
        tokenlist[0]
        .select("div[data-role='token-description']")[0]
        .get_text(strip=True)
    )
    assert desc == "the new name"


@pytest.mark.vcr()
def test_user_settings_otp_rename_no_change(client, logged_in_dummy_user_with_otp):
    """Test renaming an otp token with no actual change"""
    tokenid = logged_in_dummy_user_with_otp.uniqueid
    desc = logged_in_dummy_user_with_otp.description

    result = client.post(
        "/user/dummy/settings/otp/rename/",
        data={"token": tokenid, "description": desc},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")
    assert len(tokenlist) == 1

    new_desc = (
        tokenlist[0]
        .select("div[data-role='token-description']")[0]
        .get_text(strip=True)
    )
    assert new_desc == desc


@pytest.mark.vcr()
def test_user_settings_otp_rename_ipaerror(client, logged_in_dummy_user_with_otp):
    """Test failure when renaming an otptoken"""
    tokenid = logged_in_dummy_user_with_otp.uniqueid
    with mock.patch("noggin.security.ipa.Client.otptoken_mod") as method:
        method.side_effect = python_freeipa.exceptions.FreeIPAError(
            message="Whoops", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/rename/",
            data={"token": tokenid},
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot rename the token.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_user_settings_otp_rename_invalid_form(client, logged_in_dummy_user_with_otp):
    """Test an invalid form when renaming an otp token"""
    result = client.post("/user/dummy/settings/otp/rename/", data={})
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Token must not be empty",
        expected_category="danger",
    )
# --- Recovery code tests ---

# These tests mock the IPA client directly instead of using VCR cassettes,
# since the recovery code routes were added after the original cassettes
# were recorded.

DUMMY_USER_RESULT = {
    "cn": ["Dummy User"],
    "displayname": ["Dummy User"],
    "uid": ["dummy"],
    "krbprincipalname": ["dummy@TINYSTAGE.TEST"],
    "mail": ["dummy@unit.tests"],
    "sn": ["User"],
    "givenname": ["Dummy"],
    "nsaccountlock": False,
    "dn": "uid=dummy,cn=users,cn=accounts,dc=tinystage,dc=test",
}

DUMMY_TOTP_TOKEN = {
    "ipatokenotpalgorithm": ["sha1"],
    "ipatokenotpdigits": ["6"],
    "ipatokentotptimestep": ["30"],
    "ipatokenuniqueid": ["totp-token-id-001"],
    "description": ["dummy's token"],
    "objectclass": ["ipatoken", "ipatokentotp", "top"],
    "ipatokenowner": ["dummy"],
    "type": "TOTP",
    "managedby_user": ["dummy"],
    "dn": "ipatokenuniqueid=totp-token-id-001,cn=otp,dc=tinystage,dc=test",
}

DUMMY_RECOVERY_TOKEN = {
    "ipatokenotpalgorithm": ["sha256"],
    "ipatokenotpdigits": ["8"],
    "ipatokenuniqueid": ["recovery-token-id-001"],
    "ipatokenhotpcounter": ["0"],
    "description": ["Recovery codes"],
    "objectclass": ["ipatoken", "ipatokenhotp", "top"],
    "ipatokenowner": ["dummy"],
    "type": "HOTP",
    "managedby_user": ["dummy"],
    "dn": "ipatokenuniqueid=recovery-token-id-001,cn=otp,dc=tinystage,dc=test",
}


@pytest.fixture
def mock_ipa_client(client, app):
    """Provide a logged-in session with a mock IPA client."""
    mock_client = mock.MagicMock()
    mock_client.ping.return_value = {"summary": "IPA server version 4.10.3"}
    mock_client.ipa_version = "IPA server version 4.10.3"
    mock_client.user_find.return_value = {"result": [DUMMY_USER_RESULT]}
    mock_client.user_show.return_value = {"result": DUMMY_USER_RESULT}

    with mock.patch("noggin.utility.controllers.maybe_ipa_session", return_value=mock_client):
        with client.session_transaction() as sess:
            sess["noggin_session"] = b"fake-session"
            sess["noggin_username"] = "dummy"
            sess["noggin_ipa_server_hostname"] = "ipa.tinystage.test"
        yield mock_client


def test_recovery_generate(client, mock_ipa_client):
    """Test generating recovery codes"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [DUMMY_TOTP_TOKEN], "count": 0}
    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "uri": "otpauth://hotp/dummy@TEST:recovery"}
    }
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    def otptoken_find_side_effect(**kwargs):
        if kwargs.get("o_type") == "hotp":
            return {"result": [], "count": 0}
        return {"result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN], "count": 2}

    ipa.otptoken_find.side_effect = otptoken_find_side_effect

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/generate",
            data={
                "gen-password": "dummy_password",
                "gen-submit": "1",
            },
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, "html.parser")
    codes = page.select('[data-role="recovery-code"]')
    assert len(codes) == 10
    for code_el in codes:
        text = code_el.get_text(strip=True)
        code_part = text.split(". ", 1)[1]
        assert len(code_part) == 8
        assert code_part.isdigit()


def test_recovery_generate_requires_auth(client, mock_ipa_client):
    """Test that wrong password is rejected"""
    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.side_effect = python_freeipa.exceptions.InvalidSessionPassword(
            message="invalid credentials", code="4242"
        )
        result = client.post(
            "/user/dummy/settings/otp/recovery/generate",
            data={
                "gen-password": "wrong_password",
                "gen-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Incorrect password",
        expected_category="danger",
    )


def test_recovery_generate_duplicate(client, mock_ipa_client):
    """Test that generating codes when recovery token already exists returns error"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [DUMMY_RECOVERY_TOKEN], "count": 1}

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/generate",
            data={
                "gen-password": "dummy_password",
                "gen-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="You already have recovery codes. Regenerate them instead.",
        expected_category="warning",
    )


def test_recovery_regenerate(client, mock_ipa_client):
    """Test regenerating recovery codes"""
    ipa = mock_ipa_client

    find_calls = [0]

    def otptoken_find_side_effect(**kwargs):
        find_calls[0] += 1
        if kwargs.get("o_type") == "hotp":
            return {"result": [DUMMY_RECOVERY_TOKEN], "count": 1}
        return {"result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN], "count": 2}

    ipa.otptoken_find.side_effect = otptoken_find_side_effect
    ipa.otptoken_del.return_value = {"result": True}
    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "uri": "otpauth://hotp/dummy@TEST:recovery"}
    }
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/regenerate",
            data={
                "regen-password": "dummy_password",
                "regen-submit": "1",
            },
        )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, "html.parser")
    codes = page.select('[data-role="recovery-code"]')
    assert len(codes) == 10


def test_recovery_regenerate_last_token(client, mock_ipa_client):
    """Test regeneration when recovery token is the last active token"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [DUMMY_RECOVERY_TOKEN], "count": 1}
    ipa.otptoken_del.side_effect = python_freeipa.exceptions.BadRequest(
        message="Server is unwilling to perform: Can't delete last active token",
        code="4242",
    )

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/regenerate",
            data={
                "regen-password": "dummy_password",
                "regen-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message=(
            "Cannot regenerate recovery codes while they are your only "
            "active token. Add a regular OTP token first."
        ),
        expected_category="warning",
    )


def test_recovery_generate_ipa_error(client, mock_ipa_client):
    """Test IPA error during recovery token creation"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [], "count": 0}
    ipa.otptoken_add.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="Cannot create the token.", code="4242"
    )

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/generate",
            data={
                "gen-password": "dummy_password",
                "gen-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot create recovery codes.",
        expected_category="danger",
    )


def test_recovery_token_hidden_from_list(client, mock_ipa_client):
    """Test that the recovery token does not appear in the regular token list"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select("div.list-group .list-group-item")
    assert len(tokenlist) == 1
    desc = tokenlist[0].select_one("div[data-role='token-description']")
    assert desc is not None
    assert "Recovery codes" not in desc.get_text(strip=True)

    recovery_section = page.select_one("#recovery-codes")
    assert recovery_section is not None


@pytest.mark.vcr()
def test_recovery_generate_no_permission(client, logged_in_dummy_user):
    """Verify that a user can't generate recovery codes for another user"""
    result = client.post(
        "/user/dudemcpants/settings/otp/recovery/generate",
        data={"gen-password": "dummy_password", "gen-submit": "1"},
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_recovery_regenerate_no_permission(client, logged_in_dummy_user):
    """Verify that a user can't regenerate recovery codes for another user"""
    result = client.post(
        "/user/dudemcpants/settings/otp/recovery/regenerate",
        data={"regen-password": "dummy_password", "regen-submit": "1"},
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dudemcpants/",
        expected_message="You do not have permission to edit this account.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_recovery_generate_invalid_form(client, logged_in_dummy_user):
    """Test that submitting the generate form without a password returns error"""
    result = client.post(
        "/user/dummy/settings/otp/recovery/generate",
        data={"gen-submit": "1"},
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="You must provide a password",
        expected_category="danger",
    )


def test_recovery_token_no_rename(client, mock_ipa_client):
    """Verify the recovery token has no rename button in the UI"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    token_items = page.select("div.list-group .list-group-item")
    assert len(token_items) == 1
    rename_buttons = token_items[0].select("button[title='Rename']")
    assert len(rename_buttons) == 1
    rename_forms = page.select(
        "form[action='/user/dummy/settings/otp/rename/'] "
        "button[value='recovery-token-id-001']"
    )
    assert len(rename_forms) == 0


def test_rename_to_recovery_description_blocked(client, mock_ipa_client):
    """Server rejects renaming a token TO the recovery description."""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN],
        "count": 1,
    }

    result = client.post(
        "/user/dummy/settings/otp/rename/",
        data={"token": "some-token-id", "description": "Recovery codes"},
    )
    assert result.status_code == 302
    assert "/user/dummy/settings/otp/" in result.headers["Location"]
    ipa.otptoken_mod.assert_not_called()


def test_recovery_codes_remaining_display(client, mock_ipa_client):
    """Verify the remaining code count appears on the OTP page"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }
    ipa.otptoken_show.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "ipatokenhotpcounter": ["3"]},
    }

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    recovery_section = page.select_one("#recovery-codes")
    assert recovery_section is not None
    text = recovery_section.get_text()
    assert "7 recovery codes remaining" in text
    badge = recovery_section.select_one("span.badge.bg-success")
    assert badge is not None
    assert badge.get_text(strip=True) == "Active"


def test_recovery_codes_remaining_low_warning(client, mock_ipa_client):
    """Verify warning badge when codes are running low"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }
    ipa.otptoken_show.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "ipatokenhotpcounter": ["8"]},
    }

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    recovery_section = page.select_one("#recovery-codes")
    text = recovery_section.get_text()
    assert "2 recovery codes remaining" in text
    assert "Consider regenerating" in text
    badge = recovery_section.select_one("span.badge.bg-warning")
    assert badge is not None
    assert badge.get_text(strip=True) == "Low"


def test_recovery_codes_remaining_zero(client, mock_ipa_client):
    """Verify display when all codes are exhausted"""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }
    ipa.otptoken_show.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "ipatokenhotpcounter": ["10"]},
    }

    result = client.get("/user/dummy/settings/otp/")
    page = BeautifulSoup(result.data, "html.parser")
    recovery_section = page.select_one("#recovery-codes")
    text = recovery_section.get_text()
    assert "Exhausted" in text
    assert "Regenerate now" in text
    badge = recovery_section.select_one("span.badge.bg-danger")
    assert badge is not None


# --- Enhancement 2: Mandatory recovery codes ---


def _confirm_otp_data(totp_secret="JBSWY3DPEHPK3PXP"):
    """Build POST data for the confirm OTP form with a valid TOTP code."""
    totp = TOTP(totp_secret)
    return {
        "confirm-description": "my token",
        "confirm-secret": totp_secret,
        "confirm-code": totp.now(),
        "confirm-submit": "1",
    }


def test_mandatory_recovery_codes_on_first_token(
    client, mock_ipa_client, app, monkeypatch
):
    """With OTP_REQUIRE_RECOVERY_CODES enabled, confirming the first OTP token
    auto-generates recovery codes and shows the modal."""
    ipa = mock_ipa_client
    monkeypatch.setitem(app.config, 'OTP_REQUIRE_RECOVERY_CODES', True)

    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_TOTP_TOKEN, "uri": "otpauth://totp/dummy@TEST:token"}
    }

    find_calls = [0]

    def otptoken_find_side_effect(**kwargs):
        find_calls[0] += 1
        if find_calls[0] == 1:
            return {"result": [DUMMY_TOTP_TOKEN], "count": 1}
        return {"result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN], "count": 2}

    ipa.otptoken_find.side_effect = otptoken_find_side_effect
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    result = client.post(
        "/user/dummy/settings/otp/",
        data=_confirm_otp_data(),
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, "html.parser")
    modal = page.select_one("#recovery-codes-modal")
    assert modal is not None
    codes = page.select('[data-role="recovery-code"]')
    assert len(codes) == 10


def test_mandatory_recovery_codes_disabled(
    client, mock_ipa_client, app, monkeypatch
):
    """With OTP_REQUIRE_RECOVERY_CODES disabled (default), confirming the first
    token redirects with a warning flash instead of auto-generating codes."""
    ipa = mock_ipa_client
    monkeypatch.setitem(app.config, 'OTP_REQUIRE_RECOVERY_CODES', False)

    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_TOTP_TOKEN, "uri": "otpauth://totp/dummy@TEST:token"}
    }
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN],
        "count": 1,
    }

    result = client.post(
        "/user/dummy/settings/otp/",
        data=_confirm_otp_data(),
    )
    assert result.status_code == 302
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 2
    assert messages[0] == ("success", "The token has been created.")
    assert messages[1][0] == "warning"
    assert "recovery codes" in messages[1][1].lower()


def test_mandatory_recovery_codes_already_has_recovery(
    client, mock_ipa_client, app, monkeypatch
):
    """With OTP_REQUIRE_RECOVERY_CODES enabled, if user already has a recovery
    token, normal redirect with no auto-generation."""
    ipa = mock_ipa_client
    monkeypatch.setitem(app.config, 'OTP_REQUIRE_RECOVERY_CODES', True)

    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_TOTP_TOKEN, "uri": "otpauth://totp/dummy@TEST:token"}
    }
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN],
        "count": 2,
    }

    result = client.post(
        "/user/dummy/settings/otp/",
        data=_confirm_otp_data(),
    )
    assert result.status_code == 302
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    assert messages[0] == ("success", "The token has been created.")



def test_recovery_regenerate_delete_error(client, mock_ipa_client):
    """IPA error deleting old recovery token during regeneration."""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [DUMMY_RECOVERY_TOKEN], "count": 1}
    ipa.otptoken_del.side_effect = python_freeipa.exceptions.FreeIPAError(
        message="Cannot delete token", code="4242"
    )

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/regenerate",
            data={
                "regen-password": "dummy_password",
                "regen-submit": "1",
            },
        )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Cannot regenerate recovery codes.",
        expected_category="danger",
    )


def test_mandatory_recovery_codes_auto_generate_failure(
    client, mock_ipa_client, app, monkeypatch
):
    """With OTP_REQUIRE_RECOVERY_CODES enabled, if auto-creating recovery codes
    fails, the user gets a warning flash and redirect instead of codes modal."""
    ipa = mock_ipa_client
    monkeypatch.setitem(app.config, 'OTP_REQUIRE_RECOVERY_CODES', True)

    add_calls = [0]

    def otptoken_add_side_effect(**kwargs):
        add_calls[0] += 1
        if add_calls[0] == 1:
            return {
                "result": {
                    **DUMMY_TOTP_TOKEN,
                    "uri": "otpauth://totp/dummy@TEST:token",
                }
            }
        raise python_freeipa.exceptions.FreeIPAError(
            message="Cannot create token", code="4242"
        )

    ipa.otptoken_add.side_effect = otptoken_add_side_effect
    ipa.otptoken_find.return_value = {
        "result": [DUMMY_TOTP_TOKEN],
        "count": 1,
    }

    result = client.post(
        "/user/dummy/settings/otp/",
        data=_confirm_otp_data(),
    )
    assert result.status_code == 302
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 2
    assert messages[0] == ("success", "The token has been created.")
    assert messages[1][0] == "warning"
    assert "recovery codes" in messages[1][1].lower()


def test_recovery_generate_cache_control(client, mock_ipa_client):
    """Recovery code responses include Cache-Control: no-store."""
    ipa = mock_ipa_client
    ipa.otptoken_find.return_value = {"result": [DUMMY_TOTP_TOKEN], "count": 0}
    ipa.otptoken_add.return_value = {
        "result": {**DUMMY_RECOVERY_TOKEN, "uri": "otpauth://hotp/dummy@TEST:recovery"}
    }
    ipa.otptoken_show.return_value = {"result": {**DUMMY_RECOVERY_TOKEN}}

    def otptoken_find_side_effect(**kwargs):
        if kwargs.get("o_type") == "hotp":
            return {"result": [], "count": 0}
        return {"result": [DUMMY_TOTP_TOKEN, DUMMY_RECOVERY_TOKEN], "count": 2}

    ipa.otptoken_find.side_effect = otptoken_find_side_effect

    with mock.patch("noggin.controller.user_otp.maybe_ipa_login") as login_mock:
        login_mock.return_value = ipa
        result = client.post(
            "/user/dummy/settings/otp/recovery/generate",
            data={
                "gen-password": "dummy_password",
                "gen-submit": "1",
            },
        )
    assert result.status_code == 200
    assert result.headers.get("Cache-Control") == "no-store"

