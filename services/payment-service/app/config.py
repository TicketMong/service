import os


class Settings:
    service_name = "payment-service"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./payment_service.db")
    jwt_secret = os.getenv("JWT_SECRET", "ticketing-dev-secret")
    jwt_issuer = os.getenv("JWT_ISSUER", "auth-service")
    jwt_roles = {"CUSTOMER", "PROVIDER", "ADMIN"}


settings = Settings()
