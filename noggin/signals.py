from blinker import Namespace, ANY

from noggin_messages import UserCreateV1
from noggin.utility import messaging


noggin_signals = Namespace()


user_registered = noggin_signals.signal('user-registered')


@user_registered.connect_via(ANY)
def send_registered_message(sender, **kwargs):
    user = sender
    messaging.publish(
        UserCreateV1({"msg": {"agent": user.username, "user": user.username}})
    )
