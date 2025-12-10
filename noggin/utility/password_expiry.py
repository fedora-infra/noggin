from datetime import datetime, timezone
from flask import current_app, render_template
from flask_mail import Message
from noggin.app import mailer

def send_password_expiry_notifications(ipa):
    """
    Query IPA for users whose passwords are expiring soon
    and send reminder emails.
    """
    config = current_app.config
    thresholds = parse_thresholds(
        config.get("PASSWORD_EXPIRY_REMINDER_DAYS", "7,3,1")
    )

    users = ipa.user_find(whoami=False, all=True).get("result", [])

    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for user in users:
        expires_list = user.get("krbpasswordexpiration")
        if not expires_list:
            continue

        expires = expires_list[0]

        expires = expires.replace(hour=0, minute=0, second=0, microsecond=0)

        days_left = (expires - now).days
        if days_left in thresholds:
            send_password_expiry_email(user, days_left)



def parse_thresholds(threshold_str):
    return [int(x.strip()) for x in threshold_str.split(",")]


def send_password_expiry_email(user, days_left):
    email_addr = user.get("mail", [None])[0]
    if not email_addr:
        return

    context = {"user": user, "days_left": days_left}

    message = Message(
        subject=f"Your Noggin password expires in {days_left} days",
        recipients=[email_addr],
        body=render_template("password-expiry-email.txt", **context),
        html=render_template("password-expiry-email.html", **context),
    )

    mailer.send(message)

if __name__ == "__main__":
    from noggin.app import create_app
    from flask import current_app

    app = create_app()
    with app.app_context():
        ipa = current_app.extensions["ipa"]
        send_password_expiry_notifications(ipa)