import hashlib

from pyotp import HOTP


def generate_recovery_codes(secret_b32: str, count: int) -> list[str]:
    if count <= 0:
        return []
    hotp = HOTP(secret_b32, digits=8, digest=hashlib.sha256)
    return [hotp.at(i) for i in range(count)]
