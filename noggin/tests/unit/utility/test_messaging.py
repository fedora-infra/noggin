from unittest import mock

from fedora_messaging import exceptions as fml_exceptions

from noggin_messages import MemberSponsorV1
from noggin.utility import messaging


def test_publish():
    with mock.patch("fedora_messaging.api.publish") as api_publish:
        messaging.publish(
            MemberSponsorV1(
                {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
            )
        )
        api_publish.assert_called_once()


def test_publish_with_errors():
    with mock.patch("fedora_messaging.api.publish") as api_publish:
        api_publish.side_effect = fml_exceptions.ConnectionException()
        messaging.publish(
            MemberSponsorV1(
                {"msg": {"agent": "dummy", "user": "testuser", "group": "dummy-group"}}
            )
        )
        assert api_publish.call_count == 3
