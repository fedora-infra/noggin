import pytest

from noggin.representation.group import Group


@pytest.fixture
def dummy_group_dict():
    return {
        'cn': ['dummy-group'],
        'description': ['A dummy group'],
        'dn': 'cn=dummy-group,cn=groups,cn=accounts,dc=example,dc=com',
        'gidnumber': ['158200153'],
        'ipauniqueid': ['ee0338e4-3cff-11ea-a002-52540019b1a3'],
        'member_user': ['dummy', 'testuser'],
        'membermanager_user': ['dummy'],
        'objectclass': [
            'top',
            'groupofnames',
            'nestedgroup',
            'ipausergroup',
            'ipaobject',
            'posixgroup',
        ],
    }


def test_group(dummy_group_dict):
    """Test the Group representation"""
    group = Group(dummy_group_dict)
    assert group.name == "dummy-group"
    assert group.description == "A dummy group"
    assert group.members == ["dummy", "testuser"]
    assert group.sponsors == ["dummy"]
    assert group.dn == "cn=dummy-group,cn=groups,cn=accounts,dc=example,dc=com"


def test_group_no_dn(dummy_group_dict):
    """Test that we fallback to gecos if there is no displayname"""
    del dummy_group_dict["dn"]
    group = Group(dummy_group_dict)
    assert group.dn is None


def test_group_eq(dummy_group_dict):
    """Test that Groups can be compared based on their content"""
    group_1 = Group(dummy_group_dict)
    group_2 = Group(dummy_group_dict)
    assert group_1 == group_2
