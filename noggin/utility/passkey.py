import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa, utils
from fido2 import cbor
from fido2.webauthn import AuthenticatorData

logger = logging.getLogger(__name__)

# COSE key type identifiers (RFC 9053)
COSE_KTY_OKP = 1
COSE_KTY_EC2 = 2
COSE_KTY_RSA = 3

# COSE elliptic curve identifiers
COSE_CRV_P256 = 1
COSE_CRV_ED25519 = 6

# Supported WebAuthn public key credential parameters
SUPPORTED_PUB_KEY_CRED_PARAMS = [
    {'type': 'public-key', 'alg': -7},    # ES256
    {'type': 'public-key', 'alg': -8},    # EdDSA
    {'type': 'public-key', 'alg': -257},  # RS256
]


@dataclass
class ParsedPasskey:
    raw_value: str
    credential_id: bytes
    credential_id_b64: str
    public_key_der: bytes
    key_type: str
    display_id: str


@dataclass
class RegistrationResult:
    credential_id: bytes
    public_key_cose: bytes


@dataclass
class AssertionResult:
    credential_id: bytes


def parse_passkey_attr(attr_value: str) -> Optional[ParsedPasskey]:
    """Parse one ipapasskey attribute value.

    Format: passkey:<base64-credentialId>,<base64-spkiDer>[,<base64-userId>]

    The public key field is SPKI DER (SubjectPublicKeyInfo), as validated by
    FreeIPA via synta.PublicKey.from_pem().  The optional userId field is
    ignored (only used by discoverable credentials).
    """
    if not attr_value.startswith("passkey:"):
        return None
    rest = attr_value[len("passkey:") :]
    parts = rest.split(",")
    if len(parts) < 2:
        return None
    cred_id_b64 = parts[0]
    pub_key_b64 = parts[1]
    try:
        credential_id = base64.b64decode(cred_id_b64, validate=True)
        public_key_der = base64.b64decode(pub_key_b64, validate=True)
    except (ValueError, binascii.Error):
        logger.warning("Failed to parse passkey attribute: %s", attr_value[:40])
        return None

    if not credential_id or not public_key_der:
        return None

    key_type = detect_key_type(public_key_der)
    display_id = credential_id.hex()[:16]

    return ParsedPasskey(
        raw_value=attr_value,
        credential_id=credential_id,
        credential_id_b64=cred_id_b64,
        public_key_der=public_key_der,
        key_type=key_type,
        display_id=display_id,
    )


def format_passkey_attr(credential_id: bytes, public_key_cose: bytes) -> str:
    """Format credential data as an ipapasskey attribute value.

    Converts the COSE key to SPKI DER before encoding, matching the format
    that FreeIPA validates (base64 of SubjectPublicKeyInfo DER).
    """
    spki_der = cose_to_spki_der(public_key_cose)
    cred_b64 = base64.b64encode(credential_id).decode('ascii')
    key_b64 = base64.b64encode(spki_der).decode('ascii')
    return f"passkey:{cred_b64},{key_b64}"


def detect_key_type(der_bytes: bytes) -> str:
    """Determine the algorithm from SPKI DER-encoded public key bytes."""
    try:
        pub_key = serialization.load_der_public_key(der_bytes)
        if isinstance(pub_key, ec.EllipticCurvePublicKey):
            if isinstance(pub_key.curve, ec.SECP256R1):
                return "ES256"
            return f"EC/{pub_key.curve.name}"
        elif isinstance(pub_key, ed25519.Ed25519PublicKey):
            return "EdDSA"
        elif isinstance(pub_key, rsa.RSAPublicKey):
            return "RS256"
    except Exception as e:
        logger.debug("Could not determine key type: %s", e)
    return "unknown"


def cose_to_spki_der(cose_bytes: bytes) -> bytes:
    """Convert a COSE_Key CBOR blob to DER-encoded SubjectPublicKeyInfo.

    FreeIPA stores passkey public keys as base64-encoded SPKI DER (the content
    of a PEM ``BEGIN PUBLIC KEY`` block), validated via synta.PublicKey.from_pem.
    """
    decoded = cbor.decode(cose_bytes)
    kty = decoded.get(1)

    if kty == COSE_KTY_EC2:
        crv = decoded.get(-1)
        if crv != COSE_CRV_P256:
            raise ValueError(f"Unsupported EC2 curve: {crv}")
        x_bytes = decoded.get(-2)
        y_bytes = decoded.get(-3)
        if x_bytes is None or y_bytes is None:
            raise ValueError("EC2 key missing x or y coordinate")
        x_int = int.from_bytes(x_bytes, 'big')
        y_int = int.from_bytes(y_bytes, 'big')
        pub_numbers = ec.EllipticCurvePublicNumbers(x_int, y_int, ec.SECP256R1())
        pub_key = pub_numbers.public_key()
    elif kty == COSE_KTY_OKP:
        crv = decoded.get(-1)
        if crv != COSE_CRV_ED25519:
            raise ValueError(f"Unsupported OKP curve: {crv}")
        x_bytes = decoded.get(-2)
        if x_bytes is None:
            raise ValueError("OKP key missing x coordinate")
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(x_bytes)
    elif kty == COSE_KTY_RSA:
        n_bytes = decoded.get(-1)
        e_bytes = decoded.get(-2)
        if n_bytes is None or e_bytes is None:
            raise ValueError("RSA key missing n or e")
        if len(n_bytes) < 256:
            raise ValueError("RSA modulus too small (minimum 2048 bits)")
        n_int = int.from_bytes(n_bytes, 'big')
        e_int = int.from_bytes(e_bytes, 'big')
        pub_numbers = rsa.RSAPublicNumbers(e_int, n_int)
        pub_key = pub_numbers.public_key()
    else:
        raise ValueError(f"Unsupported COSE key type: {kty}")

    return pub_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def generate_challenge() -> bytes:
    """Generate a 32-byte random challenge for WebAuthn."""
    return os.urandom(32)


def compute_user_handle(username: str, secret: bytes) -> bytes:
    """Compute a stable user handle from the username.

    Uses HMAC-SHA256 keyed by the application secret to produce a
    non-reversible, stable 32-byte user handle.
    """
    return hmac.new(secret, username.encode(), hashlib.sha256).digest()


def b64url_decode(s: str) -> bytes:
    """Decode base64url with or without padding."""
    s += '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def b64url_encode(data: bytes) -> str:
    """Encode bytes as base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def verify_registration(
    client_data_json_b64: str,
    attestation_object_b64: str,
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: str,
) -> RegistrationResult:
    """Verify a WebAuthn registration response.

    Follows W3C WebAuthn section 7.1 (simplified — no attestation
    signature verification, matching ahdapa's approach).

    Raises ValueError on any verification failure.
    """
    cdj_bytes = b64url_decode(client_data_json_b64)
    cdj = json.loads(cdj_bytes)

    if cdj.get('type') != 'webauthn.create':
        raise ValueError('clientData type must be webauthn.create')

    expected_challenge_b64url = b64url_encode(expected_challenge)
    if cdj.get('challenge') != expected_challenge_b64url:
        raise ValueError('Challenge mismatch')

    got_origin = cdj.get('origin', '').rstrip('/')
    if got_origin != expected_origin.rstrip('/'):
        raise ValueError('Origin mismatch')

    att_bytes = b64url_decode(attestation_object_b64)
    att_obj = cbor.decode(att_bytes)

    auth_data_bytes = att_obj.get('authData')
    if not auth_data_bytes or not isinstance(auth_data_bytes, bytes):
        raise ValueError('Missing authData in attestationObject')

    ad = AuthenticatorData(auth_data_bytes)

    rp_id_hash = hashlib.sha256(expected_rp_id.encode()).digest()
    if ad.rp_id_hash != rp_id_hash:
        raise ValueError('RP ID hash mismatch')

    if not ad.flags & AuthenticatorData.FLAG.UP:
        raise ValueError('User presence flag not set')

    if not ad.is_attested():
        raise ValueError('No attested credential data')

    cred_data = ad.credential_data
    if cred_data is None:
        raise ValueError('Failed to parse attested credential data')

    credential_id = bytes(cred_data.credential_id)
    public_key_cose = cbor.encode(dict(cred_data.public_key))

    return RegistrationResult(
        credential_id=credential_id,
        public_key_cose=public_key_cose,
    )


def _verify_signature(public_key_der: bytes, signed_data: bytes, signature: bytes):
    """Verify a WebAuthn assertion signature using the stored SPKI DER public key.

    Raises ValueError if the signature is invalid or the key type is unsupported.
    """
    pub_key = serialization.load_der_public_key(public_key_der)

    try:
        if isinstance(pub_key, ec.EllipticCurvePublicKey):
            der_sig = _raw_ecdsa_to_der(signature, pub_key.key_size)
            pub_key.verify(
                der_sig,
                signed_data,
                ec.ECDSA(hashes.SHA256()),
            )
        elif isinstance(pub_key, ed25519.Ed25519PublicKey):
            pub_key.verify(signature, signed_data)
        elif isinstance(pub_key, rsa.RSAPublicKey):
            pub_key.verify(
                signature,
                signed_data,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported key type: {type(pub_key)}")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Signature verification failed: {e}") from e


def _raw_ecdsa_to_der(raw_sig: bytes, key_size_bits: int) -> bytes:
    """Convert a raw ECDSA signature (r||s) to DER-encoded format.

    WebAuthn uses raw concatenated (r||s) format, while the cryptography
    library expects DER-encoded signatures.
    """
    byte_len = (key_size_bits + 7) // 8
    if len(raw_sig) != 2 * byte_len:
        raise ValueError(
            f"Invalid raw ECDSA signature length: {len(raw_sig)} "
            f"(expected {2 * byte_len})"
        )
    r = int.from_bytes(raw_sig[:byte_len], 'big')
    s = int.from_bytes(raw_sig[byte_len:], 'big')
    return utils.encode_dss_signature(r, s)


def verify_assertion(
    client_data_json_b64: str,
    authenticator_data_b64: str,
    signature_b64: str,
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: str,
    public_key_der: bytes,
    credential_id: bytes,
) -> AssertionResult:
    """Verify a WebAuthn assertion response (login).

    Follows W3C WebAuthn section 7.2.  Unlike registration, assertion
    verification MUST check the cryptographic signature.

    Raises ValueError on any verification failure.
    """
    cdj_bytes = b64url_decode(client_data_json_b64)
    cdj = json.loads(cdj_bytes)

    if cdj.get('type') != 'webauthn.get':
        raise ValueError('clientData type must be webauthn.get')

    expected_challenge_b64url = b64url_encode(expected_challenge)
    if cdj.get('challenge') != expected_challenge_b64url:
        raise ValueError('Challenge mismatch')

    got_origin = cdj.get('origin', '').rstrip('/')
    if got_origin != expected_origin.rstrip('/'):
        raise ValueError('Origin mismatch')

    auth_data_bytes = b64url_decode(authenticator_data_b64)
    ad = AuthenticatorData(auth_data_bytes)

    rp_id_hash = hashlib.sha256(expected_rp_id.encode()).digest()
    if ad.rp_id_hash != rp_id_hash:
        raise ValueError('RP ID hash mismatch')

    if not ad.flags & AuthenticatorData.FLAG.UP:
        raise ValueError('User presence flag not set')

    client_data_hash = hashlib.sha256(cdj_bytes).digest()
    signed_data = auth_data_bytes + client_data_hash

    sig_bytes = b64url_decode(signature_b64)
    _verify_signature(public_key_der, signed_data, sig_bytes)

    return AssertionResult(credential_id=credential_id)
