import pytest

from noggin.app import ipa_admin
from noggin.security.ipa_admin import IPAAdmin


def test_flask_ext(mocker):
    init_app = mocker.patch.object(IPAAdmin, "init_app")
    dummy_app = object()
    IPAAdmin(dummy_app)
    init_app.assert_called_once_with(dummy_app)


def test_wrong_attribute(app):
    with app.test_request_context('/'), pytest.raises(AttributeError):
        ipa_admin.does_not_exist
