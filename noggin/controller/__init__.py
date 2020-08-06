from flask import Blueprint, g, render_template, session

from noggin.utility.templates import gravatar


blueprint = Blueprint("root", __name__)


@blueprint.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@blueprint.app_context_processor
def inject_global_template_vars():
    return dict(
        gravatar=gravatar,
        ipa=g.ipa if 'ipa' in g else None,
        current_user=g.current_user if 'current_user' in g else None,
        current_username=session.get('noggin_username'),
    )
