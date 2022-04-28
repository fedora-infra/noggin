from noggin.representation.group import Group


def test_group(dummy_group_dict):
    """Test the Group representation"""
    group = Group(dummy_group_dict)
    assert group.name == "dummy-group"
    assert group.description == "A dummy group"
    assert group.members == ["dummy", "testuser"]
    assert group.sponsors == ["dummy"]
    assert group.dn == "cn=dummy-group,cn=groups,cn=accounts,dc=example,dc=com"
    assert group.mailing_list == 'dummygroup@lists.fedoraproject.org'
    assert group.urls == ['http://unit.tests', "https://www.dummygroup.com.au"]
    assert group.irc_channel == 'irc://irc.unit.tests/#dummy-group'


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
