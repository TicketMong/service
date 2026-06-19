from dataclasses import dataclass
from fastapi import Header, HTTPException, status
from observability import trace_recorder


@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: str


def get_user_context(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> UserContext:
    recorder = trace_recorder()
    with recorder.span(
        "ticket.dependency.user_context",
        {
            "ticket.auth.user_id_present": x_user_id is not None,
            "ticket.auth.role_present": x_user_role is not None,
        },
    ):
        if not x_user_id or not x_user_role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")
        return UserContext(user_id=x_user_id, role=x_user_role.upper())
