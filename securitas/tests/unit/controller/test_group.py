import pytest
from bs4 import BeautifulSoup

from securitas import ipa_admin


@pytest.fixture
def dummy_group():
    ipa_admin.group_add('dummy-group', description="A dummy group")
    yield
    ipa_admin.group_del('dummy-group')


@pytest.mark.vcr()
def test_groups_list(client, logged_in_dummy_user, dummy_group):
    """Test the groups list: /groups/"""
    result = client.get('/groups/')
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.collection li[data-group-name='dummy-group']")
    assert len(groups) == 1
    group_link = groups[0].find("a")
    assert group_link is not None
    assert group_link.get_text(strip=True) == "dummy-group"
    assert group_link["href"] == "/group/dummy-group/"
    group_dn = group_link.find_next_sibling("p", attrs={"data-role": "dn"})
    assert (
        group_dn.get_text(strip=True)
        == "cn=dummy-group,cn=groups,cn=accounts,dc=example,dc=com"
    )
    group_mc = group_link.find_next_sibling("p", attrs={"data-role": "members-count"})
    assert group_mc.get_text(strip=True) == "0 members"
    group_desc = group_link.find_next_sibling("p", attrs={"data-role": "description"})
    assert group_desc.get_text(strip=True) == "A dummy group"


@pytest.mark.vcr()
def test_group(client, logged_in_dummy_user, dummy_group):
    """Test the group detail page: /group/<groupname>"""
    result = client.get('/group/dummy-group/')
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Group: dummy-group - The Fedora Project'
