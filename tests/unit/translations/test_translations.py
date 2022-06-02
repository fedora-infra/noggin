import os

import pytest
from babel.messages.frontend import compile_catalog
from bs4 import BeautifulSoup

import noggin

from ..utilities import assert_redirects_with_flash


@pytest.fixture
def compile_catalogs():
    cmd = compile_catalog()
    cmd.directory = os.path.abspath(os.path.join(noggin.__path__[0], "translations"))
    cmd.domain = ["messages"]
    cmd.run()


@pytest.mark.vcr()
def test_translation_in_code_french(
    client, logged_in_dummy_user_with_otp, compile_catalogs
):
    """Test translations are working if the string is in the code"""
    headers = {"Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3"}
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": logged_in_dummy_user_with_otp.uniqueid},
        headers=headers,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Désolé, vous ne pouvez pas désactiver votre dernier jeton actif.",
        expected_category="warning",
    )


def test_translation_in_template_french(client, compile_catalogs):
    """Test translations are working if the string is in the template"""
    headers = {"Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3"}
    result = client.get("/this-should-give-a-404", headers=headers)
    assert result.status_code == 404
    page = BeautifulSoup(result.data, 'html.parser')
    message = page.select_one(".alert.alert-danger")
    assert (
        message.get_text(strip=True)
        == "404Cette page n'a pas été trouvée. Et voilà, tu as tout gâché."
    )
