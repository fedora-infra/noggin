import base64
import hashlib
import json
import struct

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from fido2 import cbor

from noggin.utility.passkey import (
    AssertionResult,
    b64url_decode,
    b64url_encode,
    compute_user_handle,
    cose_to_spki_der,
    detect_key_type,
    format_passkey_attr,
    parse_passkey_attr,
    verify_assertion,
    verify_registration,
)

# ── Test fixtures ────────────────────────────────────────────────────────


# P-256 generator point (a valid point on the curve)
_P256_GX = bytes.fromhex(
    '6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296'
)
_P256_GY = bytes.fromhex(
    '4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5'
)


def _make_cose_key(kty=2, alg=-7, crv=1):
    """Build a COSE_Key CBOR blob for testing."""
    if kty == 2:  # EC2
        key = {1: kty, 3: alg, -1: crv, -2: _P256_GX, -3: _P256_GY}
    elif kty == 1:  # OKP
        key = {1: kty, 3: alg, -1: crv, -2: b'\x01' * 32}
    elif kty == 3:  # RSA
        key = {1: kty, 3: alg, -1: b'\x01' * 256, -2: b'\x01\x00\x01'}
    else:
        key = {1: kty, 3: alg}
    return cbor.encode(key)


def _make_ec_spki_der():
    """Build an EC P-256 SPKI DER from known COSE key bytes."""
    cose = _make_cose_key(kty=2, alg=-7, crv=1)
    return cose_to_spki_der(cose)


def _make_ed25519_spki_der():
    """Build an Ed25519 SPKI DER from known COSE key bytes."""
    cose = _make_cose_key(kty=1, alg=-8, crv=6)
    return cose_to_spki_der(cose)


def _make_rsa_spki_der():
    """Build an RSA SPKI DER from known COSE key bytes."""
    cose = _make_cose_key(kty=3, alg=-257)
    return cose_to_spki_der(cose)


CRED_ID = b'\x03' * 32
CRED_ID_B64 = base64.b64encode(CRED_ID).decode()
ES256_COSE = _make_cose_key(kty=2, alg=-7, crv=1)
ES256_SPKI = _make_ec_spki_der()
ES256_SPKI_B64 = base64.b64encode(ES256_SPKI).decode()
PASSKEY_VALUE = f"passkey:{CRED_ID_B64},{ES256_SPKI_B64}"

RP_ID = "example.com"
ORIGIN = "https://accounts.example.com"
CHALLENGE = b'\x04' * 32


def _build_auth_data(
    rp_id=RP_ID, flags=0x41, counter=0, cred_id=CRED_ID, cose_key=None
):
    """Build raw authData bytes."""
    if cose_key is None:
        cose_key = ES256_COSE
    rp_id_hash = hashlib.sha256(rp_id.encode()).digest()
    return (
        rp_id_hash
        + bytes([flags])
        + struct.pack('>I', counter)
        + b'\x00' * 16  # AAGUID
        + struct.pack('>H', len(cred_id))
        + cred_id
        + cose_key
    )


def _build_auth_data_minimal(rp_id=RP_ID, flags=0x01, counter=0):
    """Build raw authData bytes without attested credential data."""
    rp_id_hash = hashlib.sha256(rp_id.encode()).digest()
    return rp_id_hash + bytes([flags]) + struct.pack('>I', counter)


def _build_attestation(
    rp_id=RP_ID,
    challenge=CHALLENGE,
    origin=ORIGIN,
    cdj_type='webauthn.create',
    flags=0x41,
    include_cred_data=True,
):
    """Build base64url-encoded clientDataJSON and attestationObject."""
    challenge_b64url = b64url_encode(challenge)
    cdj = json.dumps(
        {'type': cdj_type, 'challenge': challenge_b64url, 'origin': origin}
    )
    cdj_b64url = b64url_encode(cdj.encode())

    if include_cred_data:
        auth_data = _build_auth_data(rp_id=rp_id, flags=flags)
    else:
        auth_data = _build_auth_data_minimal(rp_id=rp_id, flags=flags)
    att_obj = cbor.encode({'fmt': 'none', 'attStmt': {}, 'authData': auth_data})
    att_obj_b64url = b64url_encode(att_obj)

    return cdj_b64url, att_obj_b64url


# ── cose_to_spki_der ───────────────────────────────────────────────────


def test_cose_to_spki_der_es256():
    cose = _make_cose_key(kty=2, alg=-7, crv=1)
    spki = cose_to_spki_der(cose)
    assert spki[0] == 0x30  # DER SEQUENCE tag
    assert len(spki) == 91  # P-256 SPKI is always 91 bytes
    key = serialization.load_der_public_key(spki)
    assert isinstance(key, ec.EllipticCurvePublicKey)
    assert isinstance(key.curve, ec.SECP256R1)


def test_cose_to_spki_der_eddsa():
    cose = _make_cose_key(kty=1, alg=-8, crv=6)
    spki = cose_to_spki_der(cose)
    assert spki[0] == 0x30
    assert len(spki) == 44  # Ed25519 SPKI is always 44 bytes
    key = serialization.load_der_public_key(spki)
    assert isinstance(key, ed25519.Ed25519PublicKey)


def test_cose_to_spki_der_rs256():
    cose = _make_cose_key(kty=3, alg=-257)
    spki = cose_to_spki_der(cose)
    assert spki[0] == 0x30
    key = serialization.load_der_public_key(spki)
    assert isinstance(key, rsa.RSAPublicKey)


def test_cose_to_spki_der_unsupported_kty():
    cose = cbor.encode({1: 99, 3: -7})
    with pytest.raises(ValueError, match="Unsupported COSE key type"):
        cose_to_spki_der(cose)


def test_cose_to_spki_der_unsupported_ec_curve():
    cose = _make_cose_key(kty=2, alg=-7, crv=99)
    with pytest.raises(ValueError, match="Unsupported EC2 curve"):
        cose_to_spki_der(cose)


def test_cose_to_spki_der_unsupported_okp_curve():
    cose = _make_cose_key(kty=1, alg=-8, crv=99)
    with pytest.raises(ValueError, match="Unsupported OKP curve"):
        cose_to_spki_der(cose)


# ── parse_passkey_attr ───────────────────────────────────────────────────


def test_parse_passkey_attr_valid():
    result = parse_passkey_attr(PASSKEY_VALUE)
    assert result is not None
    assert result.credential_id == CRED_ID
    assert result.credential_id_b64 == CRED_ID_B64
    assert result.public_key_der == ES256_SPKI
    assert result.key_type == "ES256"
    assert result.display_id == CRED_ID.hex()[:16]
    assert result.raw_value == PASSKEY_VALUE


def test_parse_passkey_attr_with_userid():
    userid_b64 = base64.b64encode(b'\x05' * 16).decode()
    value = f"passkey:{CRED_ID_B64},{ES256_SPKI_B64},{userid_b64}"
    result = parse_passkey_attr(value)
    assert result is not None
    assert result.credential_id == CRED_ID
    assert result.key_type == "ES256"
    assert result.raw_value == value


def test_parse_passkey_attr_invalid_prefix():
    assert parse_passkey_attr("notpasskey:abc,def") is None


def test_parse_passkey_attr_no_comma():
    assert parse_passkey_attr("passkey:abc") is None


def test_parse_passkey_attr_invalid_base64():
    assert parse_passkey_attr("passkey:!!!,!!!") is None


def test_parse_passkey_attr_empty_after_prefix():
    assert parse_passkey_attr("passkey:") is None


# ── format_passkey_attr ──────────────────────────────────────────────────


def test_format_passkey_attr():
    result = format_passkey_attr(CRED_ID, ES256_COSE)
    assert result.startswith("passkey:")
    parts = result[len("passkey:") :].split(",")
    assert len(parts) == 2
    cred_id_decoded = base64.b64decode(parts[0])
    assert cred_id_decoded == CRED_ID
    spki_decoded = base64.b64decode(parts[1])
    assert spki_decoded[0] == 0x30  # DER SEQUENCE


def test_format_parse_roundtrip():
    formatted = format_passkey_attr(CRED_ID, ES256_COSE)
    parsed = parse_passkey_attr(formatted)
    assert parsed is not None
    assert parsed.credential_id == CRED_ID
    assert parsed.key_type == "ES256"


# ── detect_key_type ──────────────────────────────────────────────────────


def test_detect_key_type_es256():
    spki = _make_ec_spki_der()
    assert detect_key_type(spki) == "ES256"


def test_detect_key_type_eddsa():
    spki = _make_ed25519_spki_der()
    assert detect_key_type(spki) == "EdDSA"


def test_detect_key_type_rs256():
    spki = _make_rsa_spki_der()
    assert detect_key_type(spki) == "RS256"


def test_detect_key_type_invalid_der():
    assert detect_key_type(b'\xff\xff') == "unknown"


# ── compute_user_handle ──────────────────────────────────────────────────


TEST_SECRET = b'test-secret-key-for-unit-tests'


def test_compute_user_handle_length():
    handle = compute_user_handle("testuser", TEST_SECRET)
    assert len(handle) == 32


def test_compute_user_handle_deterministic():
    assert compute_user_handle("alice", TEST_SECRET) == compute_user_handle("alice", TEST_SECRET)


def test_compute_user_handle_different_users():
    assert compute_user_handle("alice", TEST_SECRET) != compute_user_handle("bob", TEST_SECRET)


# ── b64url helpers ───────────────────────────────────────────────────────


def test_b64url_roundtrip():
    data = b'\x00\x01\x02\xff\xfe\xfd'
    assert b64url_decode(b64url_encode(data)) == data


def test_b64url_no_padding():
    encoded = b64url_encode(b'\x00' * 3)
    assert '=' not in encoded


# ── verify_registration ─────────────────────────────────────────────────


def test_verify_registration_valid():
    cdj_b64, att_b64 = _build_attestation()
    result = verify_registration(
        client_data_json_b64=cdj_b64,
        attestation_object_b64=att_b64,
        expected_challenge=CHALLENGE,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
    )
    assert result.credential_id == CRED_ID
    assert len(result.public_key_cose) > 0
    decoded = cbor.decode(result.public_key_cose)
    assert decoded[1] == 2  # kty: EC2


def test_verify_registration_wrong_challenge():
    cdj_b64, att_b64 = _build_attestation()
    with pytest.raises(ValueError, match="Challenge mismatch"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=b'\xff' * 32,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )


def test_verify_registration_wrong_origin():
    cdj_b64, att_b64 = _build_attestation()
    with pytest.raises(ValueError, match="Origin mismatch"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin="https://evil.example.com",
        )


def test_verify_registration_wrong_rp_id():
    cdj_b64, att_b64 = _build_attestation()
    with pytest.raises(ValueError, match="RP ID hash mismatch"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=CHALLENGE,
            expected_rp_id="wrong.example.com",
            expected_origin=ORIGIN,
        )


def test_verify_registration_wrong_type():
    cdj_b64, att_b64 = _build_attestation(cdj_type='webauthn.get')
    with pytest.raises(ValueError, match="clientData type"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )


def test_verify_registration_no_user_presence():
    cdj_b64, att_b64 = _build_attestation(flags=0x40)  # AT set but UP not set
    with pytest.raises(ValueError, match="User presence"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )


def test_verify_registration_no_attested_data():
    cdj_b64, att_b64 = _build_attestation(
        flags=0x01, include_cred_data=False
    )  # UP set but AT not set, no credential data bytes
    with pytest.raises(ValueError, match="(attested credential data|No attested)"):
        verify_registration(
            client_data_json_b64=cdj_b64,
            attestation_object_b64=att_b64,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )


# ── verify_assertion ───────────────────────────────────────────────────


def _make_assertion(
    rp_id=RP_ID,
    challenge=CHALLENGE,
    origin=ORIGIN,
    cdj_type='webauthn.get',
    flags=0x01,
    counter=1,
    private_key=None,
    public_key_der=None,
):
    """Build a complete WebAuthn assertion with a real signature."""
    if private_key is None:
        private_key = ec.generate_private_key(ec.SECP256R1())
    if public_key_der is None:
        public_key_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    rp_id_hash = hashlib.sha256(rp_id.encode()).digest()
    auth_data = rp_id_hash + bytes([flags]) + struct.pack('>I', counter)

    challenge_b64url = b64url_encode(challenge)
    cdj = json.dumps(
        {'type': cdj_type, 'challenge': challenge_b64url, 'origin': origin}
    )
    cdj_bytes = cdj.encode()
    client_data_hash = hashlib.sha256(cdj_bytes).digest()

    signed_data = auth_data + client_data_hash

    from cryptography.hazmat.primitives.asymmetric import utils as asym_utils

    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        from cryptography.hazmat.primitives import hashes

        der_sig = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))
        r, s = asym_utils.decode_dss_signature(der_sig)
        byte_len = (private_key.key_size + 7) // 8
        raw_sig = r.to_bytes(byte_len, 'big') + s.to_bytes(byte_len, 'big')
    elif isinstance(private_key, ed25519.Ed25519PrivateKey):
        raw_sig = private_key.sign(signed_data)
    elif isinstance(private_key, rsa.RSAPrivateKey):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        raw_sig = private_key.sign(
            signed_data, padding.PKCS1v15(), hashes.SHA256()
        )
    else:
        raise TypeError(f"Unsupported key type: {type(private_key)}")

    return {
        'client_data_json_b64': b64url_encode(cdj_bytes),
        'authenticator_data_b64': b64url_encode(auth_data),
        'signature_b64': b64url_encode(raw_sig),
        'public_key_der': public_key_der,
    }


def test_verify_assertion_es256():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    result = verify_assertion(
        credential_id=CRED_ID,
        expected_challenge=CHALLENGE,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        **assertion,
    )
    assert isinstance(result, AssertionResult)
    assert result.credential_id == CRED_ID


def test_verify_assertion_eddsa():
    private_key = ed25519.Ed25519PrivateKey.generate()
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    result = verify_assertion(
        credential_id=CRED_ID,
        expected_challenge=CHALLENGE,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        **assertion,
    )
    assert result.credential_id == CRED_ID


def test_verify_assertion_rs256():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    result = verify_assertion(
        credential_id=CRED_ID,
        expected_challenge=CHALLENGE,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        **assertion,
    )
    assert result.credential_id == CRED_ID


def test_verify_assertion_wrong_challenge():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    with pytest.raises(ValueError, match="Challenge mismatch"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=b'\xff' * 32,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            **assertion,
        )


def test_verify_assertion_wrong_origin():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    with pytest.raises(ValueError, match="Origin mismatch"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin="https://evil.example.com",
            **assertion,
        )


def test_verify_assertion_wrong_rp_id():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    with pytest.raises(ValueError, match="RP ID hash mismatch"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=CHALLENGE,
            expected_rp_id="wrong.example.com",
            expected_origin=ORIGIN,
            **assertion,
        )


def test_verify_assertion_wrong_type():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(
        private_key=private_key, public_key_der=pub_der, cdj_type='webauthn.create'
    )
    with pytest.raises(ValueError, match="clientData type"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            **assertion,
        )


def test_verify_assertion_no_user_presence():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(
        private_key=private_key, public_key_der=pub_der, flags=0x00
    )
    with pytest.raises(ValueError, match="User presence"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            **assertion,
        )


def test_verify_assertion_invalid_signature():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion = _make_assertion(private_key=private_key, public_key_der=pub_der)
    # Use a different key's public key to cause signature mismatch
    other_key = ec.generate_private_key(ec.SECP256R1())
    other_pub_der = other_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assertion['public_key_der'] = other_pub_der
    with pytest.raises(ValueError, match="Signature verification failed"):
        verify_assertion(
            credential_id=CRED_ID,
            expected_challenge=CHALLENGE,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            **assertion,
        )
