import pytest

from securitas.representation.user import User


@pytest.fixture
def dummy_user_dict():
    return {
        'cn': ['Dummy User'],
        'displayname': ['Dummy User'],
        'dn': 'uid=dummy,cn=users,cn=accounts,dc=example,dc=com',
        'fascreationtime': ['20200122162312Z'],
        'fasgithubusername': ['dummy'],
        'fasgitlabusername': ['dummy'],
        'fasgpgkeyid': ['key1', 'key2'],
        'fasircnick': ['dummy'],
        'faslocale': ['en-US'],
        'fasrhbzemail': ['dummy@example.com'],
        'fastimezone': ['UTC'],
        'gecos': ['Dummy User'],
        'gidnumber': ['158200186'],
        'givenname': ['Dummy'],
        'has_keytab': True,
        'has_password': True,
        'homedirectory': ['/home/dummy'],
        'initials': ['DU'],
        'ipauniqueid': ['7ce42ff4-3d33-11ea-9ce7-52540019b1a3'],
        'krbcanonicalname': ['dummy@EXAMPLE.COM'],
        'krblastpwdchange': ['20200122162313Z'],
        'krbpasswordexpiration': ['20200421162313Z'],
        'krbprincipalname': ['dummy@EXAMPLE.COM'],
        'loginshell': ['/bin/bash'],
        'mail': ['dummy@example.com'],
        'memberof_group': ['ipausers'],
        'nsaccountlock': False,
        'objectclass': [
            'top',
            'person',
            'organizationalperson',
            'inetorgperson',
            'inetuser',
            'posixaccount',
            'krbprincipalaux',
            'krbticketpolicyaux',
            'ipaobject',
            'ipasshuser',
            'fasuser',
            'ipaSshGroupOfPubKeys',
            'mepOriginEntry',
        ],
        'preserved': False,
        'sn': ['User'],
        'uid': ['dummy'],
        'uidnumber': ['158200186'],
    }


def test_user(dummy_user_dict):
    """Test the User representation"""
    user = User(dummy_user_dict)
    assert user.username == "dummy"
    assert user.firstname == "Dummy"
    assert user.lastname == "User"
    assert user.name == "Dummy User"
    assert user.mail == "dummy@example.com"
    assert user.timezone == "UTC"
    assert user.locale == "en-US"
    assert user.ircnick == "dummy"
    assert user.gpgkeys == ["key1", "key2"]
    assert user.groups == ["ipausers"]
    assert user.github == "dummy"
    assert user.gitlab == "dummy"
    assert user.rhbz_mail == "dummy@example.com"


def test_user_no_displayname(dummy_user_dict):
    """Test that we fallback to gecos if there is no displayname"""
    del dummy_user_dict["displayname"]
    dummy_user_dict["gecos"] = ["GCOS"]
    user = User(dummy_user_dict)
    assert user.name == "GCOS"


def test_user_no_displayname_no_gcos(dummy_user_dict):
    """Test that we fallback to cn if there is no displayname nor gcos"""
    del dummy_user_dict["displayname"]
    del dummy_user_dict["gecos"]
    dummy_user_dict["cn"] = ["CN"]
    user = User(dummy_user_dict)
    assert user.name == "CN"


def test_user_no_displayname_no_gcos_no_cn(dummy_user_dict):
    """Test that we fallback to cn if there is no displayname nor gcos"""
    del dummy_user_dict["displayname"]
    del dummy_user_dict["gecos"]
    del dummy_user_dict["cn"]
    user = User(dummy_user_dict)
    assert user.name is None
