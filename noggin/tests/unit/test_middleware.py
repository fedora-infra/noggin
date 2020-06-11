import python_freeipa
from bs4 import BeautifulSoup


def test_ipa_error(client, mocker):
    """Test the error page for IPA exceptions"""
    maybe_ipa_session = mocker.patch("noggin.controller.root.maybe_ipa_session")
    maybe_ipa_session.side_effect = python_freeipa.exceptions.FreeIPAError

    result = client.get('/')
    assert result.status_code == 500
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'IPA Error - noggin'
