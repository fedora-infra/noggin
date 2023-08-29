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
# e.g. chat.fedoraproject.org, chat.opensuse.org
CHAT_MATRIX_TO_ARGS = "web-instance[element.io]=app.element.io"

STAGE_USERS_ROLE = "Stage User Managers"

TEMPLATES_CUSTOM_DIRECTORIES = []
ACCEPT_IMAGES_FROM = []

BASSET_URL = None
SPAMCHECK_TOKEN_EXPIRATION = 60  # in minutes

# Cheat code to toggle Fedora Messaging support
FEDORA_MESSAGING_ENABLED = False

# Captcha 
CAPTCHA_CONFIG = {
    'SECRET_CAPTCHA_KEY': 'LONG_KEY', # Used for JWT encoding/
    'CAPTCHA_LENGTH': 6, # CAPTCHA text length
    'CAPTCHA_DIGITS': False, # Include digits in the character pool?
    'EXPIRE_SECONDS': 600, # CAPTCHA expiration time in seconds
    # 'EXPIRE_MINUTES': 10 # Also supported for backwards compatibility
    # 'EXCLUDE_VISUALLY_SIMILAR': True # Optional exclude visually similar characters like 0OIl
    # 'ONLY_UPPERCASE': True # Optional only use uppercase characters
    # 'CHARACTER_POOL': 'AaBbCc123' # Optional specify character pool
}