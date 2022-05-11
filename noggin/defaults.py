# This file contains the default configuration values

TEMPLATES_AUTO_RELOAD = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
USER_DEFAULTS = {
    "locale": "en-US",
    "timezone": "UTC",
    "status_note": "active",
}
THEME = "default"
PASSWORD_POLICY = {"min": 8, "max": -1}
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

AVATAR_SERVICE_URL = "https://seccdn.libravatar.org/"
AVATAR_DEFAULT_TYPE = "robohash"

MAIL_DOMAIN_BLOCKLIST = ['fedoraproject.org']

HEALTHZ = {
    "live": "noggin.controller.root.liveness",
    "ready": "noggin.controller.root.readiness",
}

PAGE_SIZE = 30

CHAT_NETWORKS = {
    "irc": {"default_server": "irc.libera.chat"},
    "matrix": {"default_server": "fedora.im"},
}
# Link to matrix rooms and usernames using the element.io web client
# instance at chat.fedoraproject.org. Set this variable to a falsy
# value to use element.io.
CHAT_MATRIX_TO_ARGS = "web-instance[element.io]=chat.fedoraproject.org"

STAGE_USERS_ROLE = "Stage User Managers"

TEMPLATES_CUSTOM_DIRECTORIES = []
ACCEPT_IMAGES_FROM = []

BASSET_URL = None
SPAMCHECK_TOKEN_EXPIRATION = 60  # in minutes

# Cheat code to disable Fedora Messaging
FEDORA_MESSAGING_ENABLED = True
