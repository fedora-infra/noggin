import hashlib

from pyotp import HOTP

from noggin.utility.recovery_codes import generate_recovery_codes


def test_generate_recovery_codes_count():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 10)
    assert len(codes) == 10


def test_generate_recovery_codes_eight_digits():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 10)
    for code in codes:
        assert len(code) == 8
        assert code.isdigit()


def test_generate_recovery_codes_match_hotp():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 10)
    hotp = HOTP(secret, digits=8, digest=hashlib.sha256)
    for i, code in enumerate(codes):
        assert code == hotp.at(i)


def test_generate_recovery_codes_uses_sha256():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 3)
    hotp_sha1 = HOTP(secret, digits=8)
    sha1_codes = [hotp_sha1.at(i) for i in range(3)]
    assert codes != sha1_codes


def test_generate_recovery_codes_zero_count():
    secret = "JBSWY3DPEHPK3PXP"
    assert generate_recovery_codes(secret, 0) == []


def test_generate_recovery_codes_negative_count():
    secret = "JBSWY3DPEHPK3PXP"
    assert generate_recovery_codes(secret, -1) == []


def test_generate_recovery_codes_unique():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 10)
    assert len(set(codes)) == len(codes)


def test_generate_recovery_codes_custom_count():
    secret = "JBSWY3DPEHPK3PXP"
    codes = generate_recovery_codes(secret, 5)
    assert len(codes) == 5
