import os


class Settings:
    service_name = "auth-service"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./auth_service.db")
    token_ttl_seconds = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "900"))
    refresh_token_ttl_seconds = int(os.getenv("AUTH_REFRESH_TOKEN_TTL_SECONDS", "604800"))
    password_iterations = int(os.getenv("AUTH_PASSWORD_ITERATIONS", "210000"))
    jwt_secrets = {
        "STAFF": os.getenv("STAFF_JWT_SECRET", "staff-secret"),
        "PATIENT": os.getenv("PATIENT_JWT_SECRET", "patient-secret"),
        "DOCTOR": os.getenv("DOCTOR_JWT_SECRET", "doctor-secret"),
    }
    jwt_issuers = {
        "STAFF": os.getenv("STAFF_JWT_ISSUER", "staff"),
        "PATIENT": os.getenv("PATIENT_JWT_ISSUER", "patient"),
        "DOCTOR": os.getenv("DOCTOR_JWT_ISSUER", "doctor"),
    }
    expose_demo_accounts = os.getenv("AUTH_EXPOSE_DEMO_ACCOUNTS", "true").lower() == "true"


settings = Settings()
