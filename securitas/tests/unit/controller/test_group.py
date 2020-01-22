import pytest
import python_freeipa
from bs4 import BeautifulSoup

from securitas import ipa_admin


@pytest.fixture
def dummy_group():
    ipa_admin.group_add('dummy-group', description="A dummy group")
    yield
    ipa_admin.group_del('dummy-group')


@pytest.fixture
def dummy_user_as_group_manager(logged_in_dummy_user, dummy_group):
    """Make the dummy user a manager of the dummy-group group."""
    ipa_admin.group_add_member("dummy-group", users="dummy")
    ipa_admin.group_add_member_manager("dummy-group", users="dummy")
    yield


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
def test_group(client, dummy_user_as_group_manager, make_user):
    """Test the group detail page: /group/<groupname>"""
    test_users = ["testuser1", "testuser2", "testuser3"]
    # Add members to the group
    for username in test_users:
        make_user(username)
    ipa_admin.group_add_member("dummy-group", users=test_users)

    result = client.get('/group/dummy-group/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'Group: dummy-group - The Fedora Project'
    title = page.find("h3", class_="header")
    assert title.get_text(strip=True) == "dummy-group"
    assert title.find_next_sibling("p").get_text(strip=True) == "A dummy group"
    # Check the sponsors list
    sponsors = page.select("div[data-section='sponsors'] ul li")
    assert len(sponsors) == 1, str(sponsors)
    assert sponsors[0].find("a")["href"] == "/user/dummy/"
    assert sponsors[0].find("a").get_text(strip=True) == "dummy"
    # Check the members list
    members = page.select("div[data-section='members'] ul li")
    assert len(members) == len(test_users) + 1
    for index, username in enumerate(["dummy"] + test_users):
        assert members[index].find("a")["href"] == f"/user/{username}/"
        assert members[index].find("a").get_text(strip=True) == username
    # Current user is a sponsor, there must be the corresponding widgets
    assert len(page.select("button[data-target='sponsor-modal']")) == 1
    assert len(page.select("form[action='/group/dummy-group/members/']")) == 1
