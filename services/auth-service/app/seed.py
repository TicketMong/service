from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password


DEMO_USERS = [
    {
        "email": "admin@example.com",
        "password": "admin1234",
        "display_name": "Platform Admin",
        "role": "ADMIN",
        "patient_id": None,
        "doctor_id": None,
    },
    {
        "email": "customer@example.com",
        "password": "customer1234",
        "display_name": "Ticket Customer",
        "role": "CUSTOMER",
        "patient_id": None,
        "doctor_id": None,
    },
    {
        "email": "provider@example.com",
        "password": "provider1234",
        "display_name": "Concert Provider",
        "role": "PROVIDER",
        "patient_id": None,
        "doctor_id": None,
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
