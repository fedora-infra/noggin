import os
from logging.config import dictConfig

from flask import Flask
from flask_healthz import healthz
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from whitenoise import WhiteNoise

from noggin.controller import blueprint
from noggin.l10n import babel
from noggin.middleware import IPAErrorHandler
from noggin.security.ipa_admin import IPAAdmin
from noggin.themes import Theme
from noggin.utility import import_all


# Forms
csrf = CSRFProtect()

# IPA admin account
ipa_admin = IPAAdmin()

# Theme manager
theme = Theme()

# Flask-Mail
mailer = Mail()

# Catch IPA errors
ipa_error_handler = IPAErrorHandler()


def create_app(config=None):
    """See https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/"""

    app = Flask(__name__)

    # Load default configuration
    app.config.from_object("noggin.defaults")

    # Load the optional configuration file
    if "NOGGIN_CONFIG_PATH" in os.environ:
        app.config.from_envvar("NOGGIN_CONFIG_PATH")

    # Load the config passed as argument
    app.config.update(config or {})

    # Templates reloading
    if app.config.get("TEMPLATES_AUTO_RELOAD"):
        app.jinja_env.auto_reload = True

    # Logging
    if app.config.get("LOGGING"):
        dictConfig(app.config["LOGGING"])

    # Static files
    whitenoise = app.wsgi_app = WhiteNoise(
        app.wsgi_app, root=f"{app.root_path}/static/", prefix="static/"
    )

    # Extensions
    babel.init_app(app)
    app.jinja_env.add_extension("jinja2.ext.i18n")
    csrf.init_app(app)
    ipa_admin.init_app(app)
    mailer.init_app(app)
    ipa_error_handler.init_app(app)
    theme.init_app(app, whitenoise=whitenoise)

    # Register views
    import_all("noggin.controller")
    app.register_blueprint(blueprint)
    app.register_blueprint(healthz, url_prefix="/healthz")

    return app
