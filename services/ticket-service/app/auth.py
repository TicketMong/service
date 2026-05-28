from dataclasses import dataclass
from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class UserContext:
    user_id: int
    role: str


def get_user_context(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> UserContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")
    try:
        return UserContext(
            user_id=int(x_user_id),
            role=x_user_role.upper(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id must be an integer",
        ) from exc
