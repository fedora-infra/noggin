import hashlib
from urllib.parse import urlparse

from flask import current_app, Markup
from flask_babel import lazy_gettext as _


def gravatar(email, size):
    return (
        current_app.config["AVATAR_SERVICE_URL"]
        + "avatar/"
        # We use MD5 to hash email addresses because gravatar.com uses that as a key. We could use
        # SHA256 instead if we limited ourselves to using libravatar.org.
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


def format_nickname(value):
    return format_chat(value, isnick=True)


def format_channel(value):
    return format_chat(value, isnick=False)


def format_chat(value, isnick):
    url = urlparse(value)
    name = url.path.lstrip("/")
    if isnick:
        name = name.lstrip("@")
    elif not name and url.fragment:
        name = url.fragment
    scheme = url.scheme
    if not scheme:
        scheme = "irc"
    try:
        default_server = current_app.config["CHAT_NETWORKS"][scheme]["default_server"]
    except KeyError:
        raise ValueError(f"Unsupported chat protocol: '{scheme}'")
    server = url.netloc if url.netloc else default_server

    if scheme == "irc":
        protocol = "IRC"
        # https://www.w3.org/Addressing/draft-mirashi-url-irc-01.txt
        href = f"irc://{server}/{name}"
        if isnick:
            href = f"{href},isnick"
        else:
            name = f"#{name}@{server}"
    elif scheme == "matrix":
        protocol = "Matrix"
        if isnick:
            name = f"@{name}"
        else:
            name = f"#{name}"
        # https://matrix.org/docs/spec/#users
        href = f"https://matrix.to/#/{name}:{server}"
        matrixto_args = current_app.config["CHAT_MATRIX_TO_ARGS"]
        if matrixto_args:
            href = f"{href}?{matrixto_args}"
        if server != default_server or not isnick:
            name += f":{server}"
    else:
        raise ValueError(f"Can't parse '{value}'")

    title = _("%(protocol)s on %(server)s", protocol=protocol, server=server)
    return Markup(f"""<a href="{href}" title="{title}">{name}</a>""")
