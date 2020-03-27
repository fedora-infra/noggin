from flask import Flask, Blueprint
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from whitenoise import WhiteNoise

from noggin.security.ipa_admin import IPAAdmin

app = Flask(__name__)
csrf = CSRFProtect(app)

# Load defaults
app.config.from_pyfile('defaults.cfg')
# Load the configuration file
app.config.from_envvar('NOGGIN_CONFIG_PATH')

if app.config.get('TEMPLATES_AUTO_RELOAD'):
    app.jinja_env.auto_reload = True

ipa_admin = IPAAdmin(app)

# Theme support
themename = app.config.get('THEME')
blueprint = Blueprint(
    'theme',
    __name__,
    static_url_path='/theme/static',
    static_folder="themes/" + themename + "/static/",
    template_folder="themes/" + themename + "/templates/",
)
app.register_blueprint(blueprint)

# Flask-Mail
mailer = Mail(app)

# Whitenoise for static files
app.wsgi_app = WhiteNoise(
    app.wsgi_app, root=f"{app.root_path}/static", prefix="/static"
)
app.wsgi_app.add_files(
    f"{app.root_path}/themes/{themename}/static/", prefix="/theme/static"
)


# Set the version
try:
    import importlib.metadata

    __version__ = importlib.metadata.version("noggin")
except ImportError:
    try:
        import pkg_resources

        try:
            __version__ = pkg_resources.get_distribution("noggin").version
        except pkg_resources.DistributionNotFound:
            # The app is not installed, but the flask dev server can run it nonetheless.
            __version__ = None
    except ImportError:
        __version__ = None
