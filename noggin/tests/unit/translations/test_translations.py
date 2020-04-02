import pytest
from bs4 import BeautifulSoup

from noggin.tests.unit.utilities import assert_redirects_with_flash


@pytest.mark.vcr()
def test_translation_in_code_french(client, logged_in_dummy_user, dummy_user_with_otp):
    """Test translations are working if the string is in the code"""
    headers = {"Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3"}
    result = client.post(
        "/user/dummy/settings/otp/disable/",
        data={"token": dummy_user_with_otp.uniqueid},
        headers=headers,
    )
    assert_redirects_with_flash(
        result,
        expected_url="/user/dummy/settings/otp/",
        expected_message="Désolé, vous ne pouvez pas désactiver votre dernier jeton actif.",
        expected_category="warning",
    )


def test_translation_in_template_french(client):
    """Test translations are working if the string is in the template"""
    headers = {"Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3"}
    result = client.get("/this-should-give-a-404", headers=headers)
    assert result.status_code == 404
    page = BeautifulSoup(result.data, 'html.parser')
    message = page.select_one(".alert.alert-danger")
    assert (
        message.get_text(strip=True)
        == "404Cette page n'a pas été trouvée. Tu es parti et tu as tout gâché."
    )
