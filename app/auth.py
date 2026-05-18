from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from app.business import DomainError


DEMO_SECRET = "atomquest-local-demo-secret"
SECRET = os.getenv("APP_SECRET", DEMO_SECRET)


def assert_secret_is_safe(host: str | None = None) -> None:
    """Raise at startup if APP_SECRET is missing while the host is not localhost.

    Why: Render/Railway deployments without APP_SECRET set would sign tokens with a
    public default string. Failing fast protects against an attacker who knows the
    default forging admin tokens. Localhost demos still work without configuration.
    """
    if SECRET != DEMO_SECRET:
        return
    bound = (host or "").lower()
    if bound in ("", "127.0.0.1", "localhost", "::1"):
        return
    raise RuntimeError(
        "APP_SECRET environment variable must be set (and different from the demo default) "
        "when the server is not bound to localhost. Generate one with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )


SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEYLEN = 32
SCRYPT_PREFIX = "scrypt$"


def hash_password(password: str) -> str:
    """Return a salted scrypt hash. Stored as 'scrypt$<saltHex>$<hashHex>'."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEYLEN,
    )
    return f"{SCRYPT_PREFIX}{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash.

    Accepts both legacy bare-SHA-256 hashes (64 hex chars, no prefix) and the new
    scrypt format so existing demo users don't get locked out during the migration.
    """
    if not stored:
        return False
    if stored.startswith(SCRYPT_PREFIX):
        try:
            _, salt_hex, hash_hex = stored.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except (ValueError, AttributeError):
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_KEYLEN,
        )
        return hmac.compare_digest(derived, expected)
    # Legacy SHA-256 fallback (unsalted) - constant-time compared.
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def needs_password_upgrade(stored: str) -> bool:
    """True when the stored hash is in the legacy format and should be rewritten."""
    return bool(stored) and not stored.startswith(SCRYPT_PREFIX)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 12,
    }
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
        supplied = _unb64(signature_b64)
        if not hmac.compare_digest(expected, supplied):
            raise DomainError("Invalid token", 401)

        payload = json.loads(_unb64(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            raise DomainError("Session expired", 401)
        return payload
    except DomainError:
        raise
    except Exception as exc:
        raise DomainError("Invalid token", 401) from exc

