import datetime
import os
import tempfile

import pytest
import python_freeipa
from vcr import VCR

from noggin.app import create_app, ipa_admin
from noggin.representation.agreement import Agreement
from noggin.representation.otptoken import OTPToken
from noggin.security.ipa import maybe_ipa_login, untouched_ipa_client


@pytest.fixture(scope="session")
def app_config(ipa_cert):
    return dict(
        TESTING=True,
        DEBUG=True,
        WTF_CSRF_ENABLED=False,
        # IPA settings
        FREEIPA_SERVERS=['ipa.noggin.test'],
        FREEIPA_CACERT=ipa_cert,
        # Any user with admin privileges
        FREEIPA_ADMIN_USER='admin',
        FREEIPA_ADMIN_PASSWORD='password',
        # Fernet secret
        FERNET_SECRET=b'G8ObvrpEEwbjWUO9rU1qAkDQRafAFd39heVKYf6TZi8=',
        # Session secret
        SECRET_KEY=b'monkiesmonkiesmonkiesmonkiesmonkies!!!1111monkies',
        # We don't do https for testing
        SESSION_COOKIE_SECURE=False,
        # Email sender
        MAIL_DEFAULT_SENDER="Noggin <noggin@unit.tests>",
        # Set a different password policy betweed the form and the server so we can test both
        PASSWORD_POLICY={"min": 6},
        # Don't delete the role we may have in the dev env
        STAGE_USERS_ROLE="Testing Stage Users Admins",
    )


@pytest.fixture(scope="session")
def app(app_config):
    return create_app(app_config)


@pytest.fixture
def request_context(app):
    with app.test_request_context('/'):
        yield


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
        yield cert.name


@pytest.fixture
def client(app, ipa_cert):
    # app.config['FREEIPA_CACERT'] = ipa_cert
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
def ipa_testing_config(vcr_session, app):
    """Setup IPA with a testing configuration."""
    with vcr_session.use_cassette("ipa_testing_config"), app.test_request_context('/'):
        pwpolicy = ipa_admin.pwpolicy_show()
        try:
            ipa_admin.pwpolicy_mod(o_krbminpwdlife=0, o_krbpwdminlength=8)
        except python_freeipa.exceptions.BadRequest as e:
            if not e.message == "no modifications to be performed":
                raise
        # Stage users admin role
        sua_role = app.config["STAGE_USERS_ROLE"]
        ipa_admin.role_add(sua_role)
        ipa_admin.role_add_privilege(
            sua_role, o_privilege=["Stage User Administrators"]
        )
        yield
        try:
            ipa_admin.pwpolicy_mod(
                o_krbminpwdlife=pwpolicy['result']['krbminpwdlife'][0],
                o_krbpwdminlength=pwpolicy['result']['krbpwdminlength'][0],
            )
        except python_freeipa.exceptions.BadRequest as e:
            if not e.message == "no modifications to be performed":
                raise
        ipa_admin.role_del(sua_role)


@pytest.fixture
def make_user(ipa_testing_config, app):
    created_users = []

    def _make_user(name):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        password = f'{name}_password'
        ipa_admin.user_add(
            name,
            o_givenname=name.title(),
            o_sn='User',
            o_cn=f'{name.title()} User',
            o_mail=f"{name}@unit.tests",
            o_userpassword=password,
            o_loginshell='/bin/bash',
            fascreationtime=f"{now.isoformat()}Z",
        )
        ipa = untouched_ipa_client(app)
        ipa.change_password(name, password, password)
        created_users.append(name)

    yield _make_user

    for name in created_users:
        ipa_admin.user_del(name)


@pytest.fixture
def dummy_user(make_user):
    make_user("dummy")
    yield


@pytest.fixture
def dummy_user_with_case(make_user):
    make_user("duMmy")
    yield


@pytest.fixture
def make_group(ipa_testing_config, app):
    created = []

    def _make_group(name):
        result = ipa_admin.group_add(
            name,
            o_description=f"The {name} group",
            fasgroup=True,
            fasurl=f"http://{name}.unit.tests",
            fasmailinglist=f"{name}@lists.unit.tests",
            fasircchannel=f"irc://irc.unit.tests/#{name}",
        )
        created.append(name)
        return result

    yield _make_group

    for name in created:
        ipa_admin.group_del(name)


@pytest.fixture
def dummy_group(make_group):
    make_group("dummy-group")


@pytest.fixture
def dummy_user_as_group_manager(logged_in_dummy_user, dummy_group):
    """Make the dummy user a manager of the dummy-group group."""
    ipa_admin.group_add_member(a_cn="dummy-group", o_user="dummy")
    ipa_admin.group_add_member_manager(a_cn="dummy-group", o_user="dummy")
    yield


@pytest.fixture
def password_min_time(dummy_group):
    ipa_admin.pwpolicy_add(
        a_cn="dummy-group", o_krbminpwdlife=1, o_cospriority=10, o_krbpwdminlength=8
    )


@pytest.fixture
def logged_in_dummy_user(client, dummy_user, app):
    with client.session_transaction() as sess:
        ipa = maybe_ipa_login(
            app, sess, username="dummy", userpassword="dummy_password"
        )
    yield ipa
    ipa.logout()
    with client.session_transaction() as sess:
        sess.clear()


@pytest.fixture
def dummy_user_with_gpg_key(client, dummy_user):
    ipa_admin.user_mod(a_uid="dummy", fasgpgkeyid=["dummy-gpg-key-id"])


@pytest.fixture
def dummy_user_with_otp(client, dummy_user):
    result = ipa_admin.otptoken_add(
        o_ipatokenowner="dummy", o_description="dummy's token"
    )
    token = OTPToken(result["result"])
    yield token
    # Deletion needs to be done as admin to remove the last token
    ipa_admin.otptoken_del(token.uniqueid)


@pytest.fixture
def logged_in_dummy_user_with_otp(client, logged_in_dummy_user):
    ipa = logged_in_dummy_user
    result = ipa.otptoken_add(
        o_ipatokenowner="dummy",
        o_description="dummy's token",
    )
    token = OTPToken(result['result'])
    yield token
    # Deletion needs to be done as admin to remove the last token
    try:
        ipa_admin.otptoken_del(token.uniqueid)
    except python_freeipa.exceptions.NotFound:
        pass  # Already deleted


@pytest.fixture
def cleanup_dummy_tokens():
    yield
    tokens = ipa_admin.otptoken_find(a_criteria="dummy")
    for token in [OTPToken(t) for t in tokens["result"]]:
        ipa_admin.otptoken_del(a_ipatokenuniqueid=token.uniqueid)


@pytest.fixture
def dummy_agreement():
    agreement = ipa_admin.fasagreement_add(
        "dummy agreement", description="i agree to dummy"
    )
    yield Agreement(agreement)
    ipa_admin.fasagreement_del("dummy agreement")


@pytest.fixture
def dummy_group_with_agreement(dummy_group, dummy_agreement):
    ipa_admin.fasagreement_add_group("dummy agreement", group="dummy-group")
    yield
    ipa_admin.fasagreement_remove_group("dummy agreement", group="dummy-group")
