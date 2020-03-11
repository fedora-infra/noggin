import pytest

from noggin.representation.otptoken import OTPToken


@pytest.fixture
def dummy_otptoken_dict():
    return {
        'ipatokenuniqueid': ['ee0338e4-3cff-11ea-a002-52540019b1a3'],
        'description': ['pants token'],
    }


def test_otptoken(dummy_otptoken_dict):
    """Test the Group representation"""
    token = OTPToken(dummy_otptoken_dict)
    assert token.uniqueid == "ee0338e4-3cff-11ea-a002-52540019b1a3"
    assert token.description == "pants token"
