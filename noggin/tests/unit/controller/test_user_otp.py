import python_freeipa
import mock
import pytest
from bs4 import BeautifulSoup

from noggin import ipa_admin
from noggin.representation.otptoken import OTPToken
from noggin.tests.unit.utilities import (
    assert_redirects_with_flash,
    assert_form_field_error,
    assert_form_generic_error,
    otp_secret_from_uri,
    get_otp,
)


@pytest.fixture
def dummy_user_with_2_otp(client, logged_in_dummy_user, dummy_user_with_otp):
    ipa = logged_in_dummy_user
    result = ipa.otptoken_add(
        ipatokenowner="dummy",
        ipatokenotpalgorithm="sha512",
        description="dummy's other token",
    )
    token = OTPToken(result)
    yield (dummy_user_with_otp, OTPToken(result))
    try:
        ipa_admin.otptoken_del(token.uniqueid)
    except python_freeipa.exceptions.NotFound:
        pass  # already deleted, it's fine.


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
    """Test posting to the create OTP endpoint"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={"description": "pants token", "password": "dummy_password"},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    # check this is not the no tokens message
    assert "You have no OTP tokens" not in tokenlist.get_text(strip=True)
    # check we are showing 1 token
    tokens = tokenlist.select(".list-group-item .h6")
    assert len(tokens) == 1
    # check the token is in the list
    description = tokens[0].select_one("div[data-role='token-description']")
    assert description.get_text(strip=True) == "pants token"
    # check the modal is on the page
    assert len(page.select("#otp-modal")) == 1


@pytest.mark.vcr()
def test_user_settings_otp_add_second(
    client, dummy_user_with_otp, logged_in_dummy_user, cleanup_dummy_tokens
):
    """Test posting to the create OTP endpoint"""
    current_otp = get_otp(otp_secret_from_uri(dummy_user_with_otp.uri))
    result = client.post(
        "/user/dummy/settings/otp/",
        data={"description": "pants token", "password": f"dummy_password{current_otp}"},
        follow_redirects=True,
    )
    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")
    assert tokenlist is not None
    # check we are showing 2 tokens
    tokens = tokenlist.select(".list-group-item .h6 div[data-role='token-description']")
    assert len(tokens) == 2
    # check the 2nd token is in the list
    assert tokens[1].get_text(strip=True) == "pants token"
    # check the modal is on the page
    assert len(page.select("#otp-modal")) == 1


@pytest.mark.vcr()
def test_user_settings_otp_check_no_description(
    client, dummy_user_with_otp, logged_in_dummy_user, cleanup_dummy_tokens
):
    """Test an OTP token without a description"""
    current_otp = get_otp(otp_secret_from_uri(dummy_user_with_otp.uri))

    result = client.post(
        "/user/dummy/settings/otp/",
        data={"password": f"dummy_password{current_otp}"},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    tokenlist = page.select_one("div.list-group")

    assert tokenlist is not None

    tokens = tokenlist.select(".list-group-item .h6 div[data-role='token-description']")
    assert len(tokens) == 2

    assert tokens[0].get_text(strip=True) == ""
    assert tokens[1].get_text(strip=True) == "dummy's token"


@pytest.mark.vcr()
def test_user_settings_otp_check_description_escaping(
    client, dummy_user_with_otp, logged_in_dummy_user, cleanup_dummy_tokens
):
    """Test that we escape the token description when constructing the OTP URI"""
    current_otp = get_otp(otp_secret_from_uri(dummy_user_with_otp.uri))

    result = client.post(
        "/user/dummy/settings/otp/",
        data={"description": "pants token", "password": f"dummy_password{current_otp}"},
        follow_redirects=True,
    )

    page = BeautifulSoup(result.data, "html.parser")
    otp_uri = page.select_one("input#otp-uri")

    assert (
        otp_uri['value'] == "otpauth://totp/dummy@example.com:pants%20token?issuer="
        "dummy%40EXAMPLE.COM&secret=L4PD6EXABBJDSCAKS6MZQWT4RSP3PM3QW6H57UHIKFCN7I3"
        "FGKSHZCCO&digits=6&algorithm=SHA512&period=30"
    )


@pytest.mark.vcr()
def test_user_settings_otp_add_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't make an otp token. """
    result = client.post(
        "/user/dudemcpants/settings/otp/",
        data={"description": "pants token", "password": "dummy_password"},
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
    result = client.post("/user/dummy/settings/otp/", data={})
    assert_form_field_error(result, "password", "You must provide a password")


@pytest.mark.vcr()
def test_user_settings_otp_add_wrong_password(client, logged_in_dummy_user):
    """Test adding an otp token with the wrong password"""
    result = client.post(
        "/user/dummy/settings/otp/",
        data={"description": "pants token", "password": "pants"},
    )
    assert_form_field_error(result, "password", "Incorrect password")


@pytest.mark.vcr()
def test_user_settings_otp_add_invalid(client, logged_in_dummy_user):
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
            data={"description": "pants token", "password": "dummy_password"},
        )
    assert_form_generic_error(result, expected_message="Cannot create the token.")


@pytest.mark.vcr()
def test_user_settings_otp_disable_no_permission(client, logged_in_dummy_user):
    """Verify that another user can't disable an otp token. """
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
        expected_message="token must not be empty",
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
def test_user_settings_otp_disable_lasttoken(
    client, logged_in_dummy_user, dummy_user_with_otp
):
    """Test trying to disable the last token"""
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": dummy_user_with_otp.uniqueid},
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
    """Verify that another user can't delete an otp token. """
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
        expected_message="token must not be empty",
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
    client, logged_in_dummy_user, dummy_user_with_otp
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
    """Verify that another user can't enable an otp token. """
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
        expected_message="token must not be empty",
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
