from flask import Flask
from flask_wtf.csrf import CSRFProtect

from securitas.security.ipa_admin import IPAAdmin

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config.from_envvar('SECURITAS_CONFIG_PATH')
if app.config.get('TEMPLATES_AUTO_RELOAD'):
    app.jinja_env.auto_reload = True

ipa_admin = IPAAdmin(app)
