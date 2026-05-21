import os


class Settings:
    service_name = "patient-service"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./patient_service.db")


settings = Settings()
