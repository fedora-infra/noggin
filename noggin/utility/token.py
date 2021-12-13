from datetime import datetime, timedelta
from enum import Enum

import jwt
from flask import current_app


class Audience(Enum):
    """
    In JWT the audience is a constant that must remain the same between the token creator and the
    token reader, as a way to prevent token re-use.

    The longer the string, the longer the token, so we try to keep it short because some tokens end
    up in URLs and that's limited.
    """

    password_reset = "pr"
    email_validation = "ev"
    spam_check = "sc"


def make_token(data, audience, ttl=None):
    data["aud"] = audience.value
    if ttl is not None:
        data["exp"] = datetime.utcnow() + timedelta(minutes=ttl)
    token = jwt.encode(data, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token


def read_token(token, audience=None):
    return jwt.decode(
        token,
        current_app.config["SECRET_KEY"],
        algorithms=["HS256"],
        audience=audience.value,
    )


def make_password_change_token(user):
    lpc = user.last_password_change
    if lpc is not None:
        lpc = lpc.isoformat()
    return make_token(
        {"sub": user.username, "lpc": lpc},
        audience=Audience.password_reset,
    )
