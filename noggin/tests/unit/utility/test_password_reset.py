import datetime
from unittest import mock

import pytest

from noggin.app import app
from noggin.utility.password_reset import PasswordResetLock


@pytest.fixture
def tmp_lock_dir(tmp_path):
    with app.test_request_context('/'):
        with mock.patch.dict(app.config, {"PASSWORD_RESET_LOCK_DIR": tmp_path}):
            yield tmp_path


def test_lock_store(tmp_lock_dir):
    lock = PasswordResetLock("dummy")
    lock.store()
    assert tmp_lock_dir.joinpath("dummy").exists()


def test_lock_valid_until(tmp_lock_dir):
    lock = PasswordResetLock("dummy")
    lock.store()
    assert lock.valid_until() is not None
    now = datetime.datetime.now()
    assert lock.valid_until() > now


def test_lock_delete(tmp_lock_dir):
    lock = PasswordResetLock("dummy")
    lock.store()
    lock.delete()
    assert lock.valid_until() is None
