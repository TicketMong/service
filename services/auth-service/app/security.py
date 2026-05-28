import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.config import settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.password_iterations,
    )
    return f"pbkdf2_sha256${settings.password_iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False

    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(digest_b64.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def create_access_token(*, user_id: int, email: str, role: str) -> tuple[str, str, datetime]:
    now = int(time.time())
    exp = now + settings.token_ttl_seconds
    token_id = str(uuid4())
    role = role.upper()
    if role not in settings.jwt_roles:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role")
    payload = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": exp,
        "jti": token_id,
    }
    return sign_jwt(payload, settings.jwt_secret), token_id, datetime.fromtimestamp(exp, UTC)


def create_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token), datetime.fromtimestamp(int(time.time()) + settings.refresh_token_ttl_seconds, UTC)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    payload = _json_loads_b64url(payload_b64)
    role = str(payload.get("role", "")).upper()
    if role not in settings.jwt_roles:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role")

    if str(payload.get("iss", "")) != settings.jwt_issuer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")

    expected_signature = _signing_signature(f"{header_b64}.{payload_b64}", settings.jwt_secret)
    if not hmac.compare_digest(signature_b64, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload


def sign_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _b64url_json(header)
    payload_part = _b64url_json(payload)
    signature_part = _signing_signature(f"{header_part}.{payload_part}", secret)
    return f"{header_part}.{payload_part}.{signature_part}"


def _signing_signature(signing_input: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return _b64url(signature)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_json(value: dict) -> str:
    return _b64url(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _json_loads_b64url(value: str) -> dict:
    padded = value + "=" * (-len(value) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload") from exc
