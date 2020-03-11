import sys
import traceback

import backoff
from fedora_messaging import api, exceptions as fml_exceptions
from noggin import app


def backoff_hdlr(details):
    app.logger.warning(
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
    try:
        _publish(message)
    except (fml_exceptions.BaseException):
        app.logger.error(
            f"Publishing message failed. Giving up. {traceback.format_tb(sys.exc_info()[2])}"
        )
        return
