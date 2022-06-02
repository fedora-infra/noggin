import datetime
from unittest import mock

import pytest
import python_freeipa
from bs4 import BeautifulSoup
from fedora_messaging import testing as fml_testing
from flask import Markup

from noggin.app import ipa_admin
from noggin_messages import MemberSponsorV1

from ..utilities import assert_redirects_with_flash


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
    assert group_desc.get_text(strip=True) == "The dummy-group group"


@pytest.mark.vcr()
def test_groups_list_no_hidden(client, logged_in_dummy_user, dummy_group):
    """Test the groups list: /groups/"""
    result = client.get('/groups/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    group_names = [g.find("span", class_="title").get_text(strip=True) for g in groups]
    assert "ipausers" not in group_names


@pytest.mark.vcr()
def test_group_hidden(client, logged_in_dummy_user):
    """Test the hidden group: /group/ipausers"""
    result = client.get('/groups/ipausers')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_group(client, dummy_user_as_group_manager, make_user):
    """Test the group detail page: /group/<groupname>"""
    test_users = ["testuser1", "testuser2", "testuser3"]
    # Add members to the group
    for username in test_users:
        make_user(username)
    ipa_admin.group_add_member(a_cn="dummy-group", o_user=test_users)

    # Add another user, but only as a membermanager
    make_user("testuser4")
    ipa_admin.group_add_member_manager(a_cn="dummy-group", o_user=["testuser4"])

    result = client.get('/group/dummy-group/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    assert page.title
    assert page.title.string == 'dummy-group Group - noggin'
    title = page.select_one("div[data-section='identity'] > .col > h3")
    assert title.get_text(strip=True) == "dummy-group"
    assert (
        title.find_next_sibling("div").get_text(strip=True) == "The dummy-group group"
    )
    # Check the sponsors list
    sponsors = page.select(
        "div[data-section='sponsors'] .list-unstyled.row .col-lg-3.col-md-4.col-sm-6"
    )
    assert len(sponsors) == 2, str(sponsors)
    assert sponsors[0].find("a")["href"] == "/user/dummy/"
    assert sponsors[0].find("a").get_text(strip=True) == "dummy"
    assert sponsors[1].find("a")["href"] == "/user/testuser4/"
    assert sponsors[1].find("a").get_text(strip=True) == "testuser4"
    # Check the members list
    members = page.select("div[data-section='members'] ul li")
    assert len(members) == len(test_users) + 1
    for index, username in enumerate(["dummy"] + test_users):
        assert members[index].find("a")["href"] == f"/user/{username}/"
        assert members[index].find("a").get_text(strip=True) == username
    # Current user is a sponsor, there must be the corresponding add form
    assert len(page.select("form[action='/group/dummy-group/members/']")) == 1
    assert (
        page.select_one("#group-mailinglist a").get_text(strip=True)
        == "dummy-group@lists.unit.tests"
    )
    assert (
        page.select_one("#group-ircchannel a").get_text(strip=True)
        == "#dummy-group@irc.unit.tests"
    )
    assert (
        page.select_one("#group-ircchannel a")["href"]
        == "irc://irc.unit.tests/dummy-group"
    )
    assert (
        page.select_one("#group-urls a").get_text(strip=True)
        == "http://dummy-group.unit.tests"
    )


@pytest.mark.vcr()
def test_group_does_not_exist(client, logged_in_dummy_user):
    """Return a 404 when the group is not found"""
    result = client.get('/group/dummy-group/')
    assert result.status_code == 404


@pytest.mark.vcr()
def test_group_add_member(client, dummy_user_as_group_manager, make_user):
    """Test adding a member to a group"""
    make_user("testuser")
    with fml_testing.mock_sends(
        MemberSponsorV1(
            {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
        )
    ):
        result = client.post(
            '/group/dummy-group/members/', data={"new_member_username": "testuser"}
        )

    expected_message = (
        """You got it! testuser has been added to dummy-group.
    <span class='ml-auto' id="flashed-undo-button">
        <form action="/group/dummy-group/members/remove" method="post">"""
        "\n            \n           "
        """ <button type="submit" class="btn btn-outline-success btn-sm"
             name="username" value="testuser">
                Undo
            </button>
        </form>
    </span>"""
    )  # noqa

    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=Markup(expected_message),
        expected_category="success",
    )


@pytest.mark.vcr()
def test_group_add_member_hidden_group(client, dummy_user_as_group_manager, make_user):
    """Test adding a member to a group"""
    make_user("testuser")
    result = client.post(
        '/group/ipausers/members/', data={"new_member_username": "testuser"}
    )
    assert result.status_code == 404


@pytest.mark.vcr()
def test_group_add_unknown_member(client, dummy_user_as_group_manager):
    """Test adding a non-existent member to a group"""
    result = client.post(
        '/group/dummy-group/members/', data={"new_member_username": "testuser"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="User testuser was not found in the system.",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_add_member_forbidden(
    client, dummy_user_as_group_manager, dummy_group_with_agreement, make_user
):
    """Test failure when adding a member to a group"""
    make_user("testuser")
    result = client.post(
        '/group/dummy-group/members/', data={"new_member_username": "testuser"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="Unable to add user testuser: missing user agreement: dummy agreement",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_add_member_invalid(client, dummy_user_as_group_manager, make_user):
    """Test failure when adding a member to a group"""
    make_user("testuser")
    with mock.patch("noggin.security.ipa.Client.group_add_member") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            '/group/dummy-group/members/', data={"new_member_username": "testuser"}
        )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="Unable to add user testuser: something went wrong",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_add_member_invalid_form(client, dummy_user_as_group_manager):
    """Test an invalid form when adding a member to a group"""
    result = client.post('/group/dummy-group/members/', data={})
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="New member username must not be empty",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_remove_member(client, dummy_user_as_group_manager, make_user):
    """Test removing a member from a group"""
    make_user("testuser")
    ipa_admin.group_add_member(a_cn="dummy-group", o_user="testuser")
    result = client.post(
        '/group/dummy-group/members/remove', data={"username": "testuser"}
    )
    expected_message = """You got it! testuser has been removed from dummy-group.
    <span class='ml-auto' id="flashed-undo-button">
        <form action="/group/dummy-group/members/" method="post">
            <input id="username" name="username" required type="hidden" value="testuser">
            <button type="submit" class="btn btn-outline-success btn-sm"
             name="new_member_username" value="testuser">
                Undo
            </button>
        </form>
    </span>"""
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=expected_message,
        expected_category="success",
    )


@pytest.mark.vcr()
def test_group_remove_member_hidden_group(
    client, dummy_user_as_group_manager, make_user
):
    """Test removing a member from a hidden group"""
    make_user("testuser")
    result = client.post(
        '/group/ipausers/members/remove', data={"username": "testuser"}
    )
    assert result.status_code == 404


@pytest.mark.vcr()
def test_group_remove_self(client, logged_in_dummy_user, dummy_group):
    """Test a non-sponsor user removing themselves from a group"""
    ipa_admin.group_add_member("dummy-group", o_user="dummy")
    result = client.get('/group/dummy-group/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    leave_btn = page.select_one("#leave-group-btn")
    assert leave_btn.get_text(strip=True) == "Leave group"

    result = client.post(
        '/group/dummy-group/members/remove', data={"username": "dummy"}
    )

    expected_message = """You got it! dummy has been removed from dummy-group.
    <span class='ml-auto' id="flashed-undo-button">
        <form action="/group/dummy-group/members/" method="post">
            <input id="username" name="username" required type="hidden" value="dummy">
            <button type="submit" class="btn btn-outline-success btn-sm"
             name="new_member_username" value="dummy">
                Undo
            </button>
        </form>
    </span>"""

    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=expected_message,
        expected_category="success",
    )


@pytest.mark.vcr()
def test_group_remove_member_invalid(client, dummy_user_as_group_manager):
    """Test failure when removing a member from a group"""
    with mock.patch("noggin.security.ipa.Client.group_remove_member") as method:
        method.side_effect = python_freeipa.exceptions.ValidationError(
            message={
                "member": {"user": [("testuser", "something went wrong")], "group": []}
            },
            code="4242",
        )
        result = client.post(
            '/group/dummy-group/members/remove', data={"username": "testuser"}
        )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="Unable to remove user testuser: something went wrong",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_remove_member_unknown(client, dummy_user_as_group_manager):
    """Test failure when removing a member from a group"""
    result = client.post(
        '/group/dummy-group/members/remove', data={"username": "nobody"}
    )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="Unable to remove user nobody: This entry is not a member",
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_remove_member_invalid_form(client, dummy_user_as_group_manager):
    """Test an invalid form when removing a member from a group"""
    result = client.post('/group/dummy-group/members/remove', data={})
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message="Username must not be empty",
        expected_category="danger",
    )


@pytest.fixture
def make_users(ipa_testing_config, app):
    created_users = []

    def _make_users(users):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        batch_methods = [
            {
                "method": "user_add",
                "params": [
                    [name],
                    dict(
                        givenname=name.title(),
                        sn="User",
                        mail=f"{name}@unit.tests",
                        userpassword="password",
                        loginshell='/bin/bash',
                        fascreationtime=f"{now.isoformat()}Z",
                    ),
                ],
            }
            for name in users
        ]
        ipa_admin.batch(batch_methods)
        created_users.extend(users)

    yield _make_users

    batch_methods = [
        {"method": "user_del", "params": [[name], {}]} for name in created_users
    ]
    ipa_admin.batch(batch_methods)


@pytest.mark.vcr()
def test_group_many_members(client, logged_in_dummy_user, dummy_group, make_users):
    """Make sure the group page is paginated with all its members"""
    users = [f"testuser-{i}" for i in range(1, 50)]
    make_users(users)
    ipa_admin.group_add_member(a_cn="dummy-group", o_user=users)

    result = client.get('/group/dummy-group/')
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')

    # Only the first page is displayed
    members = page.select("div[data-section='members'] ul li div.card")
    assert len(members) == 48

    # But the total should be right
    total = page.select_one("div[data-section='members'] div.h4 span.badge")
    assert total.get_text(strip=True) == str(len(users))

    # The pagination bar should be present
    pagination_bar = page.select_one("ul.pagination")
    assert pagination_bar is not None
    page_items = pagination_bar.select("li.page-item")
    pages_bar_list = [
        p.select(".page-link:last-child")[0].get_text(strip=True) for p in page_items
    ]
    assert pages_bar_list == ['1(current)', '2', 'Next']


@pytest.mark.vcr()
def test_group_remove_sponsor(client, dummy_user_as_group_manager, make_user):
    """Test removing a sponsor from a group"""
    make_user("testuser")
    ipa_admin.group_add_member_manager(a_cn="dummy-group", o_user="testuser")
    result = client.post('/group/dummy-group/sponsors/remove')
    expected_message = "You got it! dummy is no longer a sponsor of dummy-group."
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=expected_message,
        expected_category="success",
    )


@pytest.mark.vcr()
def test_group_remove_sponsor_last(client, dummy_user_as_group_manager):
    """Test removing the last sponsor from a group"""
    result = client.post('/group/dummy-group/sponsors/remove')
    expected_message = "Removing the last sponsor is not allowed."
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=expected_message,
        expected_category="danger",
    )


@pytest.mark.vcr()
def test_group_remove_sponsor_unknown(
    client, logged_in_dummy_user, dummy_group, make_user
):
    """Test removing an unknown sponsor from a group"""
    make_user("testuser-1")
    ipa_admin.group_add_member_manager(a_cn="dummy-group", o_user="testuser-1")
    make_user("testuser-2")
    ipa_admin.group_add_member_manager(a_cn="dummy-group", o_user="testuser-2")
    result = client.post('/group/dummy-group/sponsors/remove')
    expected_message = (
        "Unable to remove user dummy: Insufficient access: Insufficient "
        "'write' privilege to the 'memberManager' attribute of entry "
        "'cn=dummy-group,cn=groups,cn=accounts,dc=noggin,dc=test'."
    )
    assert_redirects_with_flash(
        result,
        expected_url="/group/dummy-group/",
        expected_message=expected_message,
        expected_category="danger",
    )
