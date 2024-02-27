import pytest


@pytest.fixture
def dummy_user_dict():
    return {
        'cn': ['Dummy User'],
        'displayname': ['Dummy User'],
        'dn': 'uid=dummy,cn=users,cn=accounts,dc=example,dc=com',
        'fascreationtime': [{'__datetime__': '20200122162312Z'}],
        'fasgithubusername': ['dummy'],
        'fasgitlabusername': ['dummy'],
        'fasgpgkeyid': ['dummy-gpg-key-id-1', 'dummy-gpg-key-id-2'],
        'fasircnick': ['dummy', "dummy_"],
        'faslocale': ['en-US'],
        'fasrhbzemail': ['dummy@unit.tests'],
        'fastimezone': ['UTC'],
        'gecos': ['Dummy User'],
        'faspronoun': ['they / them / theirs'],
        'gidnumber': ['158200186'],
        'givenname': ['Dummy'],
        'has_keytab': True,
        'has_password': True,
        'homedirectory': ['/home/dummy'],
        'initials': ['DU'],
        'ipauniqueid': ['7ce42ff4-3d33-11ea-9ce7-52540019b1a3'],
        'ipasshpubkey': [
            'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCtX/SK86GrOa0xUadeZVbDXCj6wseamJQTpvjzNdKLgIBuQnA2dnR+jBS54rxUzHD1In/yI9r1VXr+KVZG4ULHmSuP3Icl0SUiVs+u+qeHP77Fa9rnQaxxCFL7uZgDSGSgMx0XtiQUrcumlD/9mrahCefU0BIKfS6e9chWwJnDnPSpyWf0y0NpaGYqPaV6Ukg2Z5tBvei6ghBb0e9Tusg9dHGvpv2B23dCzps6s5WBYY2TqjTHAEuRe6xR0agtPUE1AZ/DvSBKgwEz6RXIFOtv/fnZ0tERh238+n2nohMZNo1QAtQ6I0U9Kx2gdAgHRaMN6GzmbThji/MLgKlIJPSh',  # noqa: E501
            'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDuxGxBwWH5xMLAuIUAVU3O8ZViYWW64V3tJRob+eZngeR95PzUDeH0UlZ58bPyucpMowZNgJucsHyUjqal5bctv9Q5r224Of1R3DJqIViE16W3zncGNjbgiuc66wcO2o84HEm2Zi+v4cwU8ykM0m9zeG0257aVW4/L/fDAyR55NRJ7zLIyRmGMcjkN6j02wbGK89xXJKHMtRKa5Kg4GJx3HUae79C3B7SyoRAuyzLT6GmpMZ3XRa/khZ3t4xfUtSMV6DuvR5KJ9Wg5B20ecua1tNXOLHC3dU5L+P6Pb7+HL1sxHiYbaiBPJbosMkM2wqd3VyduQDQTO4BJyly/ruIN',  # noqa: E501
        ],
        'krbcanonicalname': ['dummy@EXAMPLE.COM'],
        'krblastpwdchange': [{'__datetime__': '20200122162313Z'}],
        'krbpasswordexpiration': [{'__datetime__': '20200421162313Z'}],
        'krbprincipalname': ['dummy@EXAMPLE.COM'],
        'loginshell': ['/bin/bash'],
        'mail': ['dummy@unit.tests'],
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
        'fasurl': ['http://unit.tests', "https://www.dummygroup.com.au"],
        'fasircchannel': ["irc://irc.unit.tests/#dummy-group"],
        'fasmailinglist': ['dummygroup@lists.fedoraproject.org'],
    }


@pytest.fixture
def dummy_agreement_dict():
    return {
        'objectclass': ['ipaassociation', 'fasagreement'],
        'ipaenabledflag': ['TRUE'],
        'ipauniqueid': ['d49ce402-aabb-11ea-88c2-525400cc96da'],
        'description': ['Particularly \nsing purpose \nhere'],
        'cn': ['CentOS Agreement'],
        'memberuser_user': [
            'andrew0',
            'austin5',
            'terri10',
            'austin15',
            'brittney20',
            'logan25',
            'tracy30',
            'alexis35',
            'james40',
            'julie45',
        ],
        'member_group': ['designers'],
        'dn': 'cn=CentOS Agreement,cn=fasagreements,dc=example,dc=com',
    }
