from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password


DEMO_USERS = [
    {
        "email": "staff",
        "password": "staff1234",
        "display_name": "원무 담당자 김민지",
        "role": "STAFF",
        "patient_id": None,
        "doctor_id": None,
    },
    {
        "email": "patient",
        "password": "patient1234",
        "display_name": "이서연",
        "role": "PATIENT",
        "patient_id": 1,
        "doctor_id": None,
    },
    {
        "email": "doctor",
        "password": "doctor1234",
        "display_name": "박준호 전문의",
        "role": "DOCTOR",
        "patient_id": None,
        "doctor_id": 10,
    },
]


def seed_demo_users(db: Session) -> None:
    for account in DEMO_USERS:
        existing = db.query(User).filter(User.email == account["email"]).one_or_none()
        if existing is not None:
            existing.display_name = account["display_name"]
            existing.password_hash = hash_password(account["password"])
            existing.role = account["role"]
            existing.patient_id = account["patient_id"]
            existing.doctor_id = account["doctor_id"]
            existing.is_active = True
            continue
        db.add(
            User(
                email=account["email"],
                password_hash=hash_password(account["password"]),
                display_name=account["display_name"],
                role=account["role"],
                patient_id=account["patient_id"],
                doctor_id=account["doctor_id"],
                is_active=True,
            )
        )
    db.commit()
