from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.config import settings


@dataclass(frozen=True)
class UserContext:
    user_id: str
    email: str
    role: str
    token_id: str


def require_user_context(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_token_id: str | None = Header(default=None, alias="X-Token-Id"),
) -> UserContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing gateway user context")
    role = x_user_role.upper()
    if role not in settings.jwt_roles:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user role")
    return UserContext(
        user_id=x_user_id,
        email=x_user_email or "",
        role=role,
        token_id=x_token_id or "",
    )


def require_role(user: UserContext, allowed_roles: set[str]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
