import datetime
import os
import tempfile

import pytest
import python_freeipa
from vcr import VCR

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


@pytest.fixture(scope="session")
def vcr_session(request):
    """Setup VCR at session-level.

    Borrowed from python-vcr.
    """
    test_dir = os.path.abspath(os.path.dirname(__file__))
    cassette_dir = os.path.join(test_dir, 'cassettes')
    kwargs = dict(
        cassette_library_dir=cassette_dir, path_transformer=VCR.ensure_suffix(".yaml")
    )
    record_mode = request.config.getoption('--vcr-record')
    if record_mode:
        kwargs['record_mode'] = record_mode
    if request.config.getoption('--disable-vcr'):
        # Set mode to record but discard all responses to disable both recording and playback
        kwargs['record_mode'] = 'new_episodes'
        kwargs['before_record_response'] = lambda *args, **kwargs: None
    vcr = VCR(**kwargs)
    yield vcr


@pytest.fixture(scope="session")
def ipa_testing_config(vcr_session):
    """Setup IPA with a testing configuration."""
    with vcr_session.use_cassette("ipa_testing_config"):
        pwpolicy = ipa_admin.pwpolicy_show()
        try:
            ipa_admin.pwpolicy_mod(krbminpwdlife=0, krbpwdminlength=8)
        except python_freeipa.exceptions.BadRequest as e:
            if not e.message == "no modifications to be performed":
                raise
            raise
        yield
        try:
            ipa_admin.pwpolicy_mod(
                krbminpwdlife=pwpolicy["krbminpwdlife"][0],
                krbpwdminlength=pwpolicy["krbpwdminlength"][0],
            )
        except python_freeipa.exceptions.BadRequest as e:
            if not e.message == "no modifications to be performed":
                raise


@pytest.fixture
def make_user(ipa_testing_config):
    created_users = []

    def _make_user(name):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        password = f'{name}_password'
        ipa_admin.user_add(
            name,
            name.title(),
            'User',
            f'{name.title()} User',
            mail="dummy@example.com",
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
def dummy_user_with_case(make_user):
    make_user("duMmy")
    yield


@pytest.fixture
def dummy_group(ipa_testing_config):
    ipa_admin.group_add('dummy-group', description="A dummy group", fasgroup=True)
    yield
    ipa_admin.group_del('dummy-group')


@pytest.fixture
def dummy_user_as_group_manager(logged_in_dummy_user, dummy_group):
    """Make the dummy user a manager of the dummy-group group."""
    ipa_admin.group_add_member("dummy-group", users="dummy")
    ipa_admin.group_add_member_manager("dummy-group", users="dummy")
    yield


@pytest.fixture
def password_min_time(dummy_group):
    ipa_admin.pwpolicy_add(
        "dummy-group", krbminpwdlife=1, cospriority=10, krbpwdminlength=8
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
