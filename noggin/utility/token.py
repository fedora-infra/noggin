from datetime import datetime, timedelta

import jwt
from flask import current_app


class JWTToken:
    def __init__(self, username):
        self.username = username

    @classmethod
    def from_user(cls, user):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_string(cls, token):
        token_data = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        return cls(**token_data)

    @property
    def data(self):
        raise NotImplementedError  # pragma: no cover

    def as_string(self):
        return str(
            jwt.encode(self.data, current_app.config["SECRET_KEY"], algorithm="HS256"),
            "ascii",
        )


class PasswordResetToken(JWTToken):
    def __init__(self, username, last_change):
        super().__init__(username)
        self.last_change = last_change

    @classmethod
    def from_user(cls, user):
        return cls(user.username, user.last_password_change)

    @property
    def data(self):
        return {"username": self.username, "last_change": self.last_change}

    def validate_last_change(self, user):
        return user.last_password_change == self.last_change


class EmailValidationToken(JWTToken):
    def __init__(self, username, mail, valid_until=None):
        super().__init__(username)
        self.mail = mail
        if valid_until is None:
            self.valid_until = datetime.utcnow() + timedelta(
                minutes=current_app.config["ACTIVATION_TOKEN_EXPIRATION"]
            )
        else:
            self.valid_until = datetime.fromtimestamp(valid_until)

    @classmethod
    def from_user(cls, user):
        return cls(user.username, user.mail)

    @property
    def data(self):
        return {
            "username": self.username,
            "mail": self.mail,
            "valid_until": self.valid_until.timestamp(),
        }

    def is_valid(self):
        return datetime.utcnow() < self.valid_until
