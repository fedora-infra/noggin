from datetime import datetime, timedelta, timezone

from noggin.utility.password_expiry import send_password_expiry_notifications


class FakeIPA:
    def __init__(self, expires_in_days):
        self.expires_in_days = expires_in_days

    def user_find(self, *args, **kwargs):
        exp = (
            datetime.now(timezone.utc).replace(microsecond=0)
            + timedelta(days=self.expires_in_days)
        )

        return {
            "result": [
                {
                    "uid": ["testuser"],
                    "mail": ["test@example.com"],
                    "krbpasswordexpiration": [exp],
                }
            ]
        }



def test_sends_email_when_expiry_matches_threshold(app, mocker):
    app.config["PASSWORD_EXPIRY_REMINDER_DAYS"] = "7,3,1"

    mocked_send = mocker.patch("noggin.utility.password_expiry.mailer.send")

    with app.app_context():
        send_password_expiry_notifications(FakeIPA(7))

    mocked_send.assert_called_once()


def test_no_email_when_expiry_not_matching_threshold(app, mocker):
    app.config["PASSWORD_EXPIRY_REMINDER_DAYS"] = "7,3,1"

    mocked_send = mocker.patch("noggin.utility.password_expiry.mailer.send")

    send_password_expiry_notifications(FakeIPA(10))

    mocked_send.assert_not_called()

def test_skips_user_with_no_expiration(app, mocker):
    """User has no krbpasswordexpiration → no email sent."""
    app.config["PASSWORD_EXPIRY_REMINDER_DAYS"] = "7,3,1"
    mocked_send = mocker.patch("noggin.utility.password_expiry.mailer.send")

    class IPA:
        def user_find(self, *args, **kwargs):
            return {"result": [{"uid": ["u"], "mail": ["x@example.com"]}]}

    with app.app_context():
        send_password_expiry_notifications(IPA())

    mocked_send.assert_not_called()

def test_skips_user_with_empty_expiration_list(app, mocker):
    """IPA sometimes returns an empty list → should skip."""
    app.config["PASSWORD_EXPIRY_REMINDER_DAYS"] = "7,3,1"
    mocked_send = mocker.patch("noggin.utility.password_expiry.mailer.send")

    class IPA:
        def user_find(self, *args, **kwargs):
            return {"result": [{
                "uid": ["u"],
                "mail": ["x@example.com"],
                "krbpasswordexpiration": []
            }]}

    with app.app_context():
        send_password_expiry_notifications(IPA())

    mocked_send.assert_not_called()

def test_skips_user_with_no_email(app, mocker):
    app.config["PASSWORD_EXPIRY_REMINDER_DAYS"] = "7,3,1"
    mocked_send = mocker.patch("noggin.utility.password_expiry.mailer.send")

    class IPA:
        def user_find(self, *args, **kwargs):
            exp = datetime.now(timezone.utc) + timedelta(days=7)
            return {"result": [{
                "uid": ["u"],
                "mail": [None],
                "krbpasswordexpiration": [exp]
            }]}

    with app.app_context():
        send_password_expiry_notifications(IPA())

    mocked_send.assert_not_called()
