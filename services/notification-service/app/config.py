import os


class Settings:
    service_name = "notification-service"
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "notification_db")
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    kafka_group_id = os.getenv("KAFKA_GROUP_ID", "notification-service")
    appointment_confirmed_topic = os.getenv("APPOINTMENT_CONFIRMED_TOPIC", "appointment-confirmed")
    prescription_issued_topic = os.getenv("PRESCRIPTION_ISSUED_TOPIC", "prescription-issued")


settings = Settings()
