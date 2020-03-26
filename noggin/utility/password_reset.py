import os
import datetime

from flask import current_app
import jwt


class PasswordResetLock:
    def __init__(self, username):
        self.username = username

    def valid_until(self):
        try:
            mtime = os.path.getmtime(self._get_file_path())
        except FileNotFoundError:
            return None
        mtime = datetime.datetime.fromtimestamp(mtime)
        return mtime + datetime.timedelta(
            minutes=current_app.config["PASSWORD_RESET_EXPIRATION"]
        )

    def store(self):
        file_path = self._get_file_path()
        try:
            os.makedirs(os.path.dirname(file_path))
        except FileExistsError:
            pass
        open(file_path, "w").close()

    def delete(self):
        os.remove(self._get_file_path())

    def _get_file_path(self):
        base_dir = current_app.config["PASSWORD_RESET_LOCK_DIR"]
        return os.path.join(base_dir, self.username)


class JWTToken:
    def __init__(self, username, last_change):
        self.username = username
        self.last_change = last_change

    @classmethod
    def from_user(cls, user):
        return cls(user.username, user.last_password_change)

    @classmethod
    def from_string(cls, token):
        token_data = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        return cls(token_data["username"], token_data["last_change"])

    @property
    def data(self):
        return {"username": self.username, "last_change": self.last_change}

    def as_string(self):
        return str(
            jwt.encode(self.data, current_app.config["SECRET_KEY"], algorithm="HS256"),
            "ascii",
        )

    def validate_last_change(self, user):
        return user.last_password_change == self.last_change
