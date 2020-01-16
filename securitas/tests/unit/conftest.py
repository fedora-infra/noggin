import os

import pytest

from securitas import ipa_admin
from securitas.app import app
from securitas.security.ipa import untouched_ipa_client


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope='module')
def vcr_cassette_dir(request):
    # Put all cassettes in cassettes/{module}/{test}.yaml
    test_dir = request.node.fspath.dirname
    module_name = request.module.__name__.split(".")[-1]
    return os.path.join(test_dir, 'cassettes', module_name)


@pytest.fixture
def dummy_user():
    try:
        ipa_admin.user_add(
            'dummy',
            'Dummy',
            'User',
            'Dummy User',
            user_password='dummy_password',
            login_shell='/bin/bash',
        )
        ipa = untouched_ipa_client(app)
        ipa.change_password('dummy', 'dummy_password', 'dummy_password')
        yield
    finally:
        ipa_admin.user_del('dummy')
