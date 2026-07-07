# This file contains the default configuration values
import socket

from flask_babel import _

TEMPLATES_AUTO_RELOAD = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
FREEIPA_DOMAIN = ".".join(socket.getfqdn().split('.')[1:])
FREEIPA_SERVERS = None
USER_DEFAULTS = {
    "locale": "en-US",
    "timezone": "UTC",
    "status_note": "active",
}
THEME = "default"
# Max password length + 6-digits OTP is 128: https://pagure.io/freeipa/issue/9600
PASSWORD_POLICY = {"min": 8, "max": 122}
PASSWORD_RESET_EXPIRATION = 10  # in minutes
# We're running in Openshift, so nobody else has access to /tmp
PASSWORD_RESET_LOCK_DIR = "/tmp/noggin-pw-reset"  # nosec
ACTIVATION_TOKEN_EXPIRATION = 30  # in minutes
REGISTRATION_OPEN = True
HIDE_GROUPS_IN = "hidden_groups"
ALLOWED_USERNAME_PATTERN = "^[a-z0-9][a-z0-9-]{3,30}[a-z0-9]$"
# This is used to build the error message
ALLOWED_USERNAME_HUMAN = ["a-z", "0-9", "-"]
# Minimum and maximum username size
ALLOWED_USERNAME_MIN_SIZE = 5
ALLOWED_USERNAME_MAX_SIZE = 32
# Forbidden username patterns
USERNAME_BLOCKLIST = []

AVATAR_SERVICE_URL = "https://seccdn.libravatar.org/"
AVATAR_DEFAULT_TYPE = "robohash"

MAIL_DOMAIN_BLOCKLIST = ['example.com', 'example.org']

HEALTHZ = {
    "live": "noggin.controller.root.liveness",
    "ready": "noggin.controller.root.readiness",
}

PAGE_SIZE = 30

CHAT_NETWORKS = {
    "irc": {"default_server": "irc.libera.chat"},
    "matrix": {"default_server": "matrix.org"},
}
# Link to matrix rooms and usernames using a element.io web client
# instance. Set this variable to whatever instance you have.
# e.g. chat.fedoraproject.org
CHAT_MATRIX_TO_ARGS = "web-instance[element.io]=app.element.io"

STAGE_USERS_ROLE = "Stage User Managers"

TEMPLATES_CUSTOM_DIRECTORIES = []
ACCEPT_IMAGES_FROM = []

BASSET_URL = None
SPAMCHECK_TOKEN_EXPIRATION = 60  # in minutes

# Cheat code to toggle Fedora Messaging support
FEDORA_MESSAGING_ENABLED = False

# Agreement warnings shown when the corresponding agreement is not signed.
# Keys must match the agreement.name from FreeIPA.
AGREEMENT_WARNINGS = {
    "Fedora Project Contributor Agreement": _(
        "Not signing the FPCA will prevent you from logging in to many Fedora "
        "services such as Pagure, Fedora Discussion, and other contributor "
        "platforms."
    ),
}

# Number of recovery codes to generate. Must not exceed the FreeIPA
# ipatokenHOTPauthWindow (default: 10).
OTP_RECOVERY_CODE_COUNT = 10
# Token description used to identify recovery tokens.
# WARNING: Changing this value after recovery tokens have been created will
# cause existing tokens to no longer be recognized as recovery tokens.
OTP_RECOVERY_DESCRIPTION = "Recovery codes"
# Warn the user when this many or fewer recovery codes remain.
OTP_RECOVERY_LOW_THRESHOLD = 3
# Auto-generate recovery codes when the user enrolls their first OTP token.
OTP_REQUIRE_RECOVERY_CODES = False
# IPA role whose members may reset another user's OTP tokens and generate
# recovery codes on their behalf.  None disables the feature.
OTP_ADMIN_RECOVERY_ROLE = None
