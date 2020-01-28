import pytest
from flask import current_app

from securitas.utility.locales import guess_locale
from securitas.utility.defaults import DEFAULTS


@pytest.mark.parametrize(
    "accepted,expected",
    [
        ("fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3", "fr-FR"),
        ("fr,en;q=0.8", "fr-FR"),
        ("fr,it-IT;q=0.8", "it-IT"),
        ("en", "en-US"),
        ("en-GB,en;q=0.8", "en-GB"),
        ("it", "it-IT"),
        ("xx", DEFAULTS["user_locale"]),
    ],
)
def test_guess_locale(client, accepted, expected):
    headers = {"Accept-Language": accepted}
    with current_app.test_request_context('/', headers=headers):
        assert guess_locale() == expected
