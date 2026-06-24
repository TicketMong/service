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
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings


ARGON2ID_MEMORY_COST_KIB = 65536
ARGON2ID_TIME_COST = 3
ARGON2ID_PARALLELISM = 4
ARGON2ID_HASH_LENGTH = 32
ARGON2ID_SALT_LENGTH = 16
LEGACY_PASSWORD_SCHEME = "pbkdf2_sha256"

_argon2id_password_hash = PasswordHash(
    (
        Argon2Hasher(
            time_cost=ARGON2ID_TIME_COST,
            memory_cost=ARGON2ID_MEMORY_COST_KIB,
            parallelism=ARGON2ID_PARALLELISM,
            hash_len=ARGON2ID_HASH_LENGTH,
            salt_len=ARGON2ID_SALT_LENGTH,
        ),
    )
)


class UnsupportedPasswordHashError(ValueError):
    pass


def hash_password(password: str) -> str:
    return hash_password_legacy_pbkdf2(password)


def hash_password_argon2id(password: str) -> str:
    return _argon2id_password_hash.hash(password)


def hash_password_legacy_pbkdf2(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.password_iterations,
    )
    return f"{LEGACY_PASSWORD_SCHEME}${settings.password_iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    scheme = identify_password_hash(password_hash)
    if scheme == "argon2id":
        try:
            return _argon2id_password_hash.verify(password, password_hash)
        except UnknownHashError as exc:
            raise UnsupportedPasswordHashError("Unsupported password hash scheme") from exc
    if scheme == LEGACY_PASSWORD_SCHEME:
        return verify_password_legacy_pbkdf2(password, password_hash)
    raise UnsupportedPasswordHashError("Unsupported password hash scheme")


def verify_password_legacy_pbkdf2(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != LEGACY_PASSWORD_SCHEME:
        return False

    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(digest_b64.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def identify_password_hash(password_hash: str) -> str:
    if password_hash.startswith("$argon2id$"):
        return "argon2id"
    scheme, separator, _rest = password_hash.partition("$")
    if separator and scheme == LEGACY_PASSWORD_SCHEME:
        return LEGACY_PASSWORD_SCHEME
    return "unknown"


def password_hash_metadata(password_hash: str) -> dict[str, str | int]:
    scheme = identify_password_hash(password_hash)
    if scheme == LEGACY_PASSWORD_SCHEME:
        return _legacy_pbkdf2_metadata(password_hash)
    if scheme == "argon2id":
        return _argon2id_metadata(password_hash)
    return {"auth.password.scheme": "unknown"}


def _legacy_pbkdf2_metadata(password_hash: str) -> dict[str, str | int]:
    try:
        scheme, iterations, _salt_b64, _digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return {"auth.password.scheme": "unknown"}

    attributes: dict[str, str | int] = {"auth.password.scheme": scheme}
    if iterations.isdigit():
        attributes["auth.password.iterations"] = int(iterations)
    return attributes


def _argon2id_metadata(password_hash: str) -> dict[str, str | int]:
    parts = password_hash.split("$")
    if len(parts) < 4:
        return {"auth.password.scheme": "unknown"}

    attributes: dict[str, str | int] = {"auth.password.scheme": "argon2id"}
    for item in parts[3].split(","):
        key, separator, value = item.partition("=")
        if not separator or not value.isdigit():
            continue
        if key == "m":
            attributes["auth.password.memory_kib"] = int(value)
        elif key == "t":
            attributes["auth.password.time_cost"] = int(value)
        elif key == "p":
            attributes["auth.password.parallelism"] = int(value)
    return attributes


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
