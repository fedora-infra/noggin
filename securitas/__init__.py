from flask import Flask, Blueprint
from flask_wtf.csrf import CSRFProtect

from securitas.security.ipa_admin import IPAAdmin

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config.from_envvar('SECURITAS_CONFIG_PATH')
if app.config.get('TEMPLATES_AUTO_RELOAD'):
    app.jinja_env.auto_reload = True

ipa_admin = IPAAdmin(app)

themename = app.config.get('THEME', 'default')
blueprint = Blueprint(
    'theme',
    __name__,
    static_url_path='/theme/static',
    static_folder="themes/" + themename + "/static/",
    template_folder="themes/" + themename + "/templates/",
)
app.register_blueprint(blueprint)

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("securitas")
except ImportError:
    try:
        import pkg_resources

        try:
            __version__ = pkg_resources.get_distribution("securitas").version
        except pkg_resources.DistributionNotFound:
            # The app is not installed, but the flask dev server can run it nonetheless.
            __version__ = None
    except ImportError:
        __version__ = None
