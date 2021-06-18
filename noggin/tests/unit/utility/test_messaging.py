from fedora_messaging import exceptions as fml_exceptions
from flask import current_app

from noggin.utility import messaging
from noggin_messages import MemberSponsorV1


def test_publish(request_context, mocker):
    api_publish = mocker.patch("fedora_messaging.api.publish")
    messaging.publish(
        MemberSponsorV1(
            {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
        )
    )
    api_publish.assert_called_once()


def test_publish_with_errors(request_context, mocker):
    api_publish = mocker.patch("fedora_messaging.api.publish")
    api_publish.side_effect = fml_exceptions.ConnectionException()
    messaging.publish(
        MemberSponsorV1(
            {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
        )
    )
    assert api_publish.call_count == 3


def test_publish_disabled(request_context, mocker):
    mocker.patch.dict(current_app.config, {"FEDORA_MESSAGING_ENABLED": False})
    api_publish = mocker.patch("fedora_messaging.api.publish")
    messaging.publish(
        MemberSponsorV1(
            {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
        )
    )
    api_publish.assert_not_called()
