import base64
import hashlib
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core import signing
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def _load_pem_key(pem_text):
    if not pem_text:
        return None
    if isinstance(pem_text, str):
        pem_text = pem_text.encode("utf-8")
    return pem_text


def _get_key_paths():
    base_dir = getattr(settings, "BASE_DIR", Path(__file__).resolve().parent.parent)
    base_dir = Path(base_dir)
    return base_dir / ".rsa_private.pem", base_dir / ".rsa_public.pem"


_KEY_ROTATION_MINUTES = 10
_CURRENT_KEYS = None
_PREVIOUS_KEYS = None
_KEYS_ROTATE_AT = None


def _now():
    return datetime.utcnow()


def _generate_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _get_rsa_keys():
    priv_pem = _load_pem_key(getattr(settings, "RSA_PRIVATE_KEY", None))
    pub_pem = _load_pem_key(getattr(settings, "RSA_PUBLIC_KEY", None))

    if priv_pem and pub_pem:
        private_key = serialization.load_pem_private_key(priv_pem, password=None)
        public_key = serialization.load_pem_public_key(pub_pem)
        return private_key, public_key

    # Rotating keys every 10 minutes (in-memory rotation)
    global _CURRENT_KEYS, _PREVIOUS_KEYS, _KEYS_ROTATE_AT
    now = _now()
    if _CURRENT_KEYS is None or _KEYS_ROTATE_AT is None or now >= _KEYS_ROTATE_AT:
        _PREVIOUS_KEYS = _CURRENT_KEYS
        _CURRENT_KEYS = _generate_keypair()
        _KEYS_ROTATE_AT = now + timedelta(minutes=_KEY_ROTATION_MINUTES)
    return _CURRENT_KEYS


def _sha256_hex(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encrypt_identity(value):
    private_key, public_key = _get_rsa_keys()
    ciphertext = public_key.encrypt(
        value.encode("utf-8"),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    return base64.b64encode(ciphertext).decode("ascii")


def sign_identity(value):
    return signing.dumps(value, salt="myHomePage.auth.identity")


def verify_signed_identity(token):
    if not token:
        return None
    try:
        return signing.loads(token, salt="myHomePage.auth.identity")
    except signing.BadSignature:
        return None


def _normalize_b64(token):
    if not token:
        return None
    token = token.strip().replace(" ", "+")
    token = token.replace("-", "+").replace("_", "/")
    pad_len = (-len(token)) % 4
    if pad_len:
        token += "=" * pad_len
    return token


def decrypt_identity(token):
    if not token:
        return None
    private_key, public_key = _get_rsa_keys()
    try:
        token = _normalize_b64(token)
        if not token:
            return None
        data = base64.b64decode(token.encode("ascii"))
        try:
            plaintext = private_key.decrypt(
                data,
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
            )
            return plaintext.decode("utf-8")
        except Exception:
            # Graceful fallback: try previous key for a short overlap window
            if _PREVIOUS_KEYS:
                prev_private, _ = _PREVIOUS_KEYS
                plaintext = prev_private.decrypt(
                    data,
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
                )
                return plaintext.decode("utf-8")
            return None
    except Exception:
        return None


def get_public_key_spki_b64():
    private_key, public_key = _get_rsa_keys()
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(der).decode("ascii")


def decrypt_login_field(token):
    return decrypt_identity(token)


def identity_digest(user):
    # Stable digest for session validation
    payload = f"{user.id}|{user.username}|{user.email or ''}"
    return _sha256_hex(payload)
