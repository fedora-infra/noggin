import pytest

from noggin.representation.user import User
from noggin.representation.group import Group


def test_diff_fields(dummy_user_dict):
    """ Check the method to compare the diff between two User objects works"""
    user = User(dummy_user_dict)

    new_data = dummy_user_dict.copy()
    new_data["fasgithubusername"] = ["newusername"]
    changed_user = User(new_data)

    diff = user.diff_fields(changed_user)
    assert diff == ['github']


def test_diff_fields_check_mismatch(dummy_user_dict, dummy_group_dict):
    """ Check we cannot diff two different objects"""
    user = User(dummy_user_dict)
    group = Group(dummy_group_dict)

    with pytest.raises(ValueError):
        user.diff_fields(group)


def test_wrong_attribute(dummy_user_dict):
    user = User(dummy_user_dict)
    with pytest.raises(AttributeError) as e:
        user.does_not_exist
    assert str(e.value) == "does_not_exist"
