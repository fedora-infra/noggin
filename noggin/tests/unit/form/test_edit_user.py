from collections import namedtuple

import pytest
from bs4 import BeautifulSoup

from noggin.form.edit_user import UserSettingsProfileForm


Obj = namedtuple("Obj", ["ircnick"])


@pytest.mark.parametrize(
    "data,expected",
    [
        # Backend has good data
        ([None, "irc:/username"], ["irc", "username"]),
        (
            [None, "irc://irc.unit.tests/username[m]"],
            ["irc", "username[m]:irc.unit.tests"],
        ),
        ([None, "matrix:/username"], ["matrix", "username"]),
        ([None, "matrix://matrix.org/username"], ["matrix", "username:matrix.org"]),
        # Backend has historic (unformatted) data
        ([None, "username"], ["irc", "username"]),
        ([None, "@username"], ["irc", "username"]),
        ([None, "username@unit.tests"], ["irc", "username:unit.tests"]),
        ([None, "username @ unit.tests"], ["irc", "username:unit.tests"]),
        # User input
        ([("irc", "username"), None], ["irc", "username"]),
        ([("irc", "@username"), None], ["irc", "username"]),
        ([("irc", "username@unit.tests"), None], ["irc", "username:unit.tests"]),
        ([("irc", "username @ unit.tests"), None], ["irc", "username:unit.tests"]),
        ([("matrix", "username"), None], ["matrix", "username"]),
        ([("matrix", "@username"), None], ["matrix", "username"]),
        ([("matrix", "username:matrix.org"), None], ["matrix", "username:matrix.org"]),
        ([("matrix", "@username:matrix.org"), None], ["matrix", "username:matrix.org"]),
        ([("matrix", "username@matrix.org"), None], ["matrix", "username:matrix.org"]),
    ],
)
def test_form_edit_user_ircnick(app, data, expected):
    formdata, obj_data = data
    obj = Obj(ircnick=[obj_data])
    if formdata is not None:
        formdata = {"ircnick-0-type": formdata[0], "ircnick-0-value": formdata[1]}
    with app.test_request_context('/', method="POST", data=formdata):
        form = UserSettingsProfileForm(obj=obj)
    expected_type, expected_value = expected
    ircnick = form.ircnick.entries[0]
    assert ircnick.subfields[0].data == expected_type
    assert ircnick.subfields[1].data == expected_value


def test_form_edit_user_ircnick_delete(app):
    obj = Obj(ircnick="testvalue")
    with app.test_request_context(
        '/', method="POST", data={"ircnick-0-type": "irc", "ircnick-0-value": ""}
    ):
        form = UserSettingsProfileForm(obj=obj)
    form.validate()
    assert "ircnick" not in form.errors
    assert form.ircnick.data == []


@pytest.mark.parametrize(
    "data,expected",
    [
        ("invalid+username", "This does not look like a valid nickname."),
        ("username@invalid+server", "This does not look like a valid server name."),
    ],
)
def test_form_edit_user_ircnick_invalid(app, data, expected):
    with app.test_request_context(
        '/', method="POST", data={"ircnick-0-type": "irc", "ircnick-0-value": data}
    ):
        form = UserSettingsProfileForm()
    form.validate()
    assert "ircnick" in form.errors
    assert form.errors["ircnick"][0] == [expected]
    html = BeautifulSoup(form.ircnick.entries[0](), 'html.parser')
    msg = html.select_one("div.invalid-feedback")
    assert msg is not None
    assert msg.get_text(strip=True) == expected


def test_form_edit_user_ircnick_valid_empty(app):
    with app.test_request_context(
        '/', method="POST", data={"ircnick-0-type": "irc", "ircnick-0-value": ""}
    ):
        form = UserSettingsProfileForm()
    form.validate()
    assert "ircnick" not in form.errors
    html = BeautifulSoup(form.ircnick.entries[0](), 'html.parser')
    msg = html.select_one("div.invalid-feedback")
    assert msg is None
