from flask import g, render_template, session

from securitas import app
from securitas.controller.authentication import login, logout  # noqa: F401
from securitas.controller.group import group, groups  # noqa: F401
from securitas.controller.password import password_reset  # noqa: F401
from securitas.controller.registration import register  # noqa: F401
from securitas.controller.root import root, search_json  # noqa: F401
from securitas.controller.user import user  # noqa: F401
from securitas.utility import gravatar


@app.context_processor
def inject_global_template_vars():
    return dict(
        gravatar=gravatar,
        ipa=g.ipa if 'ipa' in g else None,
        current_user=g.current_user if 'current_user' in g else None,
        current_username=session.get('securitas_username'),
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
