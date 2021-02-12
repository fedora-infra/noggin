import pytest
from bs4 import BeautifulSoup

from noggin.app import ipa_admin
from noggin.representation.group import Group
from noggin.utility.pagination import PagedResult, paginated_find


@pytest.fixture
def many_dummy_groups(ipa_testing_config):
    all_fas_groups = ipa_admin.group_find(fasgroup=True)["result"]

    # Don't call remote batch method with an empty list
    if all_fas_groups:
        ipa_admin.batch(
            a_methods=[
                {"method": "group_del", "params": [[entry["cn"][0]], {}]}
                for entry in all_fas_groups
            ]
        )

    group_list = [f"dummy-group-{i:02d}" for i in range(1, 11)]
    ipa_admin.batch(
        a_methods=[
            {"method": "group_add", "params": [[name], {"fasgroup": True}]}
            for name in group_list
        ]
    )

    yield

    ipa_admin.batch(
        a_methods=[
            {"method": "group_del", "params": [[name], {}]} for name in group_list
        ]
    )

    # Add back original FAS groups
    if all_fas_groups:
        ipa_admin.batch(
            a_methods=[
                {
                    "method": "group_add",
                    "params": [
                        [entry["cn"][0]],
                        {k: v for k, v in entry.items() if k != "cn"},
                    ],
                }
                for entry in all_fas_groups
            ]
        )


@pytest.mark.vcr()
def test_groups_page(client, logged_in_dummy_user, many_dummy_groups):
    """Test the paginated groups list"""
    result = client.get("/groups/?page_number=2&page_size=3")
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    group_names = [g.find("span", class_="title").get_text(strip=True) for g in groups]
    assert group_names == [
        "dummy-group-04",
        "dummy-group-05",
        "dummy-group-06",
    ]

    pagination_bar = page.select_one("ul.pagination")
    assert pagination_bar is not None
    # Prev
    prev_link = pagination_bar.select_one("li:first-child a.page-link")
    assert prev_link is not None
    assert prev_link["href"] == "/groups/?page_number=1&page_size=3"
    # Next
    next_link = pagination_bar.select_one("li:last-child a.page-link")
    assert next_link is not None
    assert next_link["href"] == "/groups/?page_number=3&page_size=3"
    # Other links
    assert len(pagination_bar.select("li.page-item")) == 6


@pytest.mark.vcr()
def test_groups_page_nopaging(client, logged_in_dummy_user, mocker):
    ipa = mocker.Mock(name="ipa")
    mocker.patch("noggin.utility.controllers.maybe_ipa_session", return_value=ipa)
    ipa.user_find.return_value = {"result": [{"uid": "dummy"}]}
    ipa.group_find.return_value = {"result": [{"cn": "dummy-1"}, {"cn": "dummy-2"}]}
    result = client.get("/groups/?page_size=0")
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    assert len(groups) == 2
    ipa.group_find.assert_called_with(fasgroup=True, all=True, sizelimit=0)
    ipa.batch.assert_not_called()


def test_pagination_result_no_paging():
    result = PagedResult(items=["dummy"], page_size=0, page_number=1)
    assert result.total_pages == 1


def test_pagination_result():
    result = PagedResult(items=["dummy"], page_size=2, page_number=1)
    assert result.page_url(0) is None
    assert result.page_url(2) is None
    assert repr(result) == "<PagedResult items=[1 items] page=1>"
    assert result == PagedResult(items=["dummy"], page_size=2, page_number=1)
    with pytest.raises(ValueError):
        result == object()


@pytest.mark.vcr()
def test_empty_result(mocker, app):
    """Don't call ipa.batch when there are no results"""
    ipa = mocker.Mock()
    ipa.group_find.return_value = {"result": []}
    with app.test_request_context("/?page_size=10"):
        result = paginated_find(ipa, Group)
    ipa.group_find.assert_called_once_with(pkey_only=True, sizelimit=0)
    ipa.batch.assert_not_called()
    assert len(result.items) == 0


@pytest.mark.vcr()
def test_mounted_subdir(client, logged_in_dummy_user, many_dummy_groups):
    """Test the pagination when the app is mounted on a subdirectory"""
    result = client.get(
        "/groups/?page_number=2&page_size=3", base_url="http://localhost/subdir"
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    # Check all links
    links = page.select("ul.pagination a.page-link")
    assert len(links) == 5
    for link in links:
        assert link["href"].startswith("/subdir/groups/?page_number=")
