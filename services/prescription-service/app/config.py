import os


class Settings:
    service_name = "prescription-service"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./prescription_service.db")
    patient_service_url = os.getenv("PATIENT_SERVICE_URL", "http://patient-service:8081")
    patient_service_timeout_seconds = float(os.getenv("PATIENT_SERVICE_TIMEOUT_SECONDS", "2"))
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    prescription_issued_topic = os.getenv("PRESCRIPTION_ISSUED_TOPIC", "prescription-issued")


settings = Settings()
