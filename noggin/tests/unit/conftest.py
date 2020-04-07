import datetime
import os
import tempfile

import pytest
import python_freeipa

from noggin import ipa_admin
from noggin.app import app
from noggin.representation.otptoken import OTPToken
from noggin.security.ipa import untouched_ipa_client, maybe_ipa_login


@pytest.fixture(scope="session")
def ipa_cert():
    """Create a CA cert usable for tests.

    The FreeIPA CA cert file must exist for client requests to work. Use the one provided by a local
    install of FreeIPA if available, use an empty file otherwise (but in that case the requests must
    have been recorded by VCR).
    """
    with tempfile.NamedTemporaryFile(
        prefix="ipa-ca-", suffix=".crt", delete=False
    ) as cert:
        if os.path.exists("/etc/ipa/ca.crt"):
            # Copy the proper CA file so tests that have no VCR cassette can run
            with open("/etc/ipa/ca.crt", "rb") as orig_ca:
                cert.write(orig_ca.read())
        else:
            # FreeIPA is not installed, this may be CI, just use an empty file
            # because VCR will mock the requests anyway.
            pass
        cert.close()
        app.config['FREEIPA_CACERT'] = cert.name
        yield


@pytest.fixture(scope="session")
def add_hidden_group():
    hidden_group = app.config.get('HIDDEN_GROUPS')
    parent_group = ipa_admin.group_find(hidden_group)
    if not parent_group:
        ipa_admin.group_add(cn=hidden_group)
    ipa_admin.group_add_member(cn=hidden_group, group="ipausers")


@pytest.fixture
def client(ipa_cert):
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
def make_user():
    created_users = []

    def _make_user(name):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        password = f'{name}_password'
        ipa_admin.user_add(
            name,
            name.title(),
            'User',
            f'{name.title()} User',
            user_password=password,
            login_shell='/bin/bash',
            fascreationtime=f"{now.isoformat()}Z",
        )
        ipa = untouched_ipa_client(app)
        ipa.change_password(name, password, password)
        created_users.append(name)

    yield _make_user

    for username in created_users:
        ipa_admin.user_del(username)


@pytest.fixture
def dummy_user(make_user):
    make_user("dummy")
    yield


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


@pytest.fixture
def no_password_min_time(dummy_group):
    ipa_admin.pwpolicy_add(
        "dummy-group", krbminpwdlife=0, cospriority=10, krbpwdminlength=8
    )


@pytest.fixture
def logged_in_dummy_user(client, dummy_user):
    with client.session_transaction() as sess:
        ipa = maybe_ipa_login(app, sess, "dummy", "dummy_password")
    yield ipa
    ipa.logout()
    with client.session_transaction() as sess:
        sess.clear()


@pytest.fixture
def dummy_user_with_gpg_key(client, dummy_user):
    ipa_admin.user_mod("dummy", fasgpgkeyid=["dummygpgkeyid"])


@pytest.fixture
def dummy_user_with_otp(client, logged_in_dummy_user):
    ipa = logged_in_dummy_user
    result = ipa.otptoken_add(
        ipatokenowner="dummy",
        ipatokenotpalgorithm='sha512',
        description="dummy's token",
    )
    token = OTPToken(result)
    yield token
    # Deletion needs to be done as admin to remove the last token
    try:
        ipa_admin.otptoken_del(token.uniqueid)
    except python_freeipa.exceptions.NotFound:
        pass  # Already deleted


@pytest.fixture
def cleanup_dummy_tokens():
    yield
    tokens = ipa_admin.otptoken_find("dummy")
    if tokens is None:
        return
    for token in [OTPToken(t) for t in tokens]:
        ipa_admin.otptoken_del(token.uniqueid)
