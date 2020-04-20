from flask import g, render_template, session

from noggin import app
from noggin.controller.authentication import otp_sync  # noqa: F401
from noggin.controller.group import group, groups  # noqa: F401
from noggin.controller.password import password_reset  # noqa: F401
from noggin.controller.registration import (  # noqa: F401
    confirm_registration,
    activate_account,
)
from noggin.controller.root import root, search_json  # noqa: F401
from noggin.controller.user import user  # noqa: F401
from noggin.utility import gravatar


@app.context_processor
def inject_global_template_vars():
    return dict(
        gravatar=gravatar,
        ipa=g.ipa if 'ipa' in g else None,
        current_user=g.current_user if 'current_user' in g else None,
        current_username=session.get('noggin_username'),
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
