import os


class Settings:
    service_name = "appointment-service"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./appointment_service.db")
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    appointment_confirmed_topic = os.getenv("APPOINTMENT_CONFIRMED_TOPIC", "appointment-confirmed")


settings = Settings()
