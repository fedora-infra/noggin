import sys
import traceback

import backoff
from fedora_messaging import api
from fedora_messaging import exceptions as fml_exceptions
from flask import current_app


def backoff_hdlr(details):
    current_app.logger.warning(
        f"Publishing message failed. Retrying. {traceback.format_tb(sys.exc_info()[2])}"
    )


@backoff.on_exception(
    backoff.expo,
    (fml_exceptions.ConnectionException, fml_exceptions.PublishException),
    max_tries=3,
    on_backoff=backoff_hdlr,
)
def _publish(message):
    api.publish(message)


def publish(message):
    if not current_app.config["FEDORA_MESSAGING_ENABLED"]:
        current_app.logger.info(
            f"Fedora Messaging is disabled, not publishing the message on {message.topic}"
        )
        return
    try:
        _publish(message)
    except (fml_exceptions.BaseException):
        current_app.logger.error(
            f"Publishing message failed. Giving up. {traceback.format_tb(sys.exc_info()[2])}"
        )
        return
