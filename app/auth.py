from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from app.business import DomainError


SECRET = os.getenv("APP_SECRET", "atomquest-local-demo-secret")


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

