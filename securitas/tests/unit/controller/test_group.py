import mock
import pytest
import python_freeipa
from bs4 import BeautifulSoup
from flask import get_flashed_messages

from securitas import ipa_admin


@pytest.mark.vcr()
def test_groups_list(client, logged_in_dummy_user, dummy_group):
    """Test the groups list: /groups/"""
    result = client.get('/groups/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    group_names = [g.find("span", class_="title").get_text(strip=True) for g in groups]
    assert "dummy-group" in group_names
    dummy_group_index = group_names.index("dummy-group")
    group_block = groups[dummy_group_index]
    group_link = group_block.find("a")
    assert group_link is not None
    assert group_link.get_text(strip=True) == "dummy-group"
    assert group_link["href"] == "/group/dummy-group/"
    group_mc = group_block.find("div", attrs={"data-role": "members-count"})
    assert group_mc.get_text(strip=True) == "0 members"
    group_desc = group_block.find("div", attrs={"data-role": "description"})
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
    sponsors = page.select("div[data-section='sponsors'] .row > div")
    assert len(sponsors) == 1, str(sponsors)
    assert sponsors[0].find("a")["href"] == "/user/dummy/"
    assert sponsors[0].find("a").get_text(strip=True) == "dummy"
    # Check the members list
    members = page.select("div[data-section='members'] ul li")
    assert len(members) == len(test_users) + 1
    for index, username in enumerate(["dummy"] + test_users):
        assert members[index].find("a")["href"] == f"/user/{username}/"
        assert members[index].find("a").get_text(strip=True) == username
    # Current user is a sponsor, there must be the corresponding add form
    assert len(page.select("form[action='/group/dummy-group/members/']")) == 1


@pytest.mark.vcr()
def test_group_does_not_exist(client, logged_in_dummy_user):
    """Return a 404 when the group is not found"""
    result = client.get('/group/dummy-group/')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_group_add_member(client, dummy_user_as_group_manager, make_user):
    """Test adding a member to a group"""
    make_user("testuser")
    result = client.post(
        '/group/dummy-group/members/', data={"new_member_username": "testuser"}
    )
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "You got it! testuser has been added to dummy-group."
    assert category == "success"


@pytest.mark.vcr()
def test_group_add_unknown_member(client, dummy_user_as_group_manager):
    """Test adding a non-existent member to a group"""
    result = client.post(
        '/group/dummy-group/members/', data={"new_member_username": "testuser"}
    )
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "User testuser was not found in the system."
    assert category == "danger"


@pytest.mark.vcr()
def test_group_add_member_invalid(client, dummy_user_as_group_manager, make_user):
    """Test failure when adding a member to a group"""
    make_user("testuser")
    with mock.patch("securitas.security.ipa.Client.group_add_member") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            '/group/dummy-group/members/', data={"new_member_username": "testuser"}
        )
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "Unable to add user testuser: something went wrong"
    assert category == "danger"


@pytest.mark.vcr()
def test_group_add_member_invalid_form(client, dummy_user_as_group_manager):
    """Test an invalid form when adding a member to a group"""
    result = client.post('/group/dummy-group/members/', data={})
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "New member username must not be empty"
    assert category == "danger"


@pytest.mark.vcr()
def test_group_remove_member(client, dummy_user_as_group_manager, make_user):
    """Test removing a member from a group"""
    make_user("testuser")
    ipa_admin.group_add_member("dummy-group", users="testuser")
    result = client.post(
        '/group/dummy-group/members/remove', data={"username": "testuser"}
    )
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "You got it! testuser has been removed from dummy-group."
    assert category == "success"


@pytest.mark.vcr()
def test_group_remove_member_invalid(client, dummy_user_as_group_manager):
    """Test failure when removing a member from a group"""
    with mock.patch("securitas.security.ipa.Client.group_remove_member") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            '/group/dummy-group/members/remove', data={"username": "testuser"}
        )
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "Unable to remove user testuser: something went wrong"
    assert category == "danger"


@pytest.mark.vcr()
def test_group_remove_member_invalid_form(client, dummy_user_as_group_manager):
    """Test an invalid form when removing a member from a group"""
    result = client.post('/group/dummy-group/members/remove', data={})
    assert result.status_code == 302
    assert result.location == f"http://localhost/group/dummy-group/"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == "Username must not be empty"
    assert category == "danger"
