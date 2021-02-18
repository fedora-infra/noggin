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

AVATAR_SERVICE_URL = "https://seccdn.libravatar.org/"
AVATAR_DEFAULT_TYPE = "robohash"

MAIL_DOMAIN_BLOCKLIST = ['fedoraproject.org']

HEALTHZ = {
    "live": "noggin.controller.root.liveness",
    "ready": "noggin.controller.root.readiness",
}

PAGE_SIZE = 30

BASSET_URL = None
SPAMCHECK_TOKEN_EXPIRATION = 60  # in minutes

# Cheat code to disable Fedora Messaging
FEDORA_MESSAGING_ENABLED = True
