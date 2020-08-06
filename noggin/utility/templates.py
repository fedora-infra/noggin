import hashlib

from flask import current_app, Markup
from flask_babel import lazy_gettext as _


def gravatar(email, size):
    return (
        current_app.config["AVATAR_SERVICE_URL"]
        + "avatar/"
        + hashlib.md5(email.lower().encode('utf8')).hexdigest()  # nosec
        + "?s="
        + str(size)
        + "&d="
        + current_app.config["AVATAR_DEFAULT_TYPE"]
    )


def undo_button(form_action, submit_name, submit_value, hidden_tag):
    """return an undo button html snippet as a string, to be used in flash messages"""

    undo_text = _("Undo")

    template = f"""
    <span class='ml-auto' id="flashed-undo-button">
        <form action="{form_action}" method="post">
            {hidden_tag}
            <button type="submit" class="btn btn-outline-success btn-sm"
             name="{submit_name}" value="{submit_value}">
                {undo_text}
            </button>
        </form>
    </span>"""
    return Markup(template)
