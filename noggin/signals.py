import time

import requests
from blinker import ANY, Namespace
from flask import current_app, request, url_for

from noggin.utility import messaging
from noggin.utility.token import Audience, make_token
from noggin_messages import UserCreateV1


noggin_signals = Namespace()

stageuser_created = noggin_signals.signal('stageuser-created')
user_registered = noggin_signals.signal('user-registered')


@user_registered.connect_via(ANY)
def send_registered_message(sender, **kwargs):
    user = sender
    messaging.publish(
        UserCreateV1({"msg": {"agent": user.username, "user": user.username}})
    )


@stageuser_created.connect_via(ANY)
def request_basset_check(sender, **kwargs):
    user = sender
    basset_url = current_app.config.get("BASSET_URL")
    if not basset_url:
        return

    token = make_token(
        {"sub": user.username},
        audience=Audience.spam_check,
        ttl=current_app.config["SPAMCHECK_TOKEN_EXPIRATION"],
    )
    user_dict = user.as_dict()
    user_dict["email"] = user_dict["mail"]
    user_dict["human_name"] = user_dict["commonname"]

    response = requests.post(
        basset_url,
        json={
            "action": "fedora.noggin.registration",
            "time": int(time.time()),
            "data": {
                "user": user_dict,
                "request_headers": dict(request.headers),
                "request_ip": request.remote_addr,
                "token": token,
                "callback": url_for('.spamcheck_hook', _external=True),
            },
        },
    )
    if not response.ok:
        current_app.logger.warning(
            "Error requesting a Basset check: "
            f"{response.status_code} {response.reason}: {response.text}"
        )
