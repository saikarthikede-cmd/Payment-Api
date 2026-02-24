from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Database configuration
    database_url: str = "postgresql+psycopg://postgres:Karthik@localhost:5432/appdb"
    
    # Order processing configuration
    enable_strict_idempotency_check: bool = False
    transaction_settlement_window: float = 0.0
    enable_graceful_degradation: bool = False
    
    # Wallet operation configuration
    wallet_operation_lock_timeout: int = 0

    # Authentication configuration
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
