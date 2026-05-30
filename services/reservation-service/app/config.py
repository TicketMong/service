from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "reservation-service"
    port: int = 8083
    database_url: str = "sqlite:///./reservation_service.db"
    kafka_bootstrap_servers: str = ""
    reservation_created_topic: str = "reservation-created"
    reservation_expired_topic: str = "reservation-expired"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
