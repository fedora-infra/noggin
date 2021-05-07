import datetime
import os

from flask import current_app


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
        try:
            os.remove(self._get_file_path())
        except FileNotFoundError:
            pass  # It's already been removed

    def _get_file_path(self):
        base_dir = current_app.config["PASSWORD_RESET_LOCK_DIR"]
        return os.path.join(base_dir, self.username)
