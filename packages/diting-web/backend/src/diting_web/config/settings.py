"""Application settings."""

from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DiTing Web"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://admin:password@localhost:5432/diting_web",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=20, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, validation_alias="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        validation_alias="JWT_SECRET_KEY",
        description="JWT secret key - MUST be changed in production",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_in_production(cls, v: str, info) -> str:
        """Validate JWT secret is not using default value in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "your-secret-key-change-in-production":
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value in production. "
                "Generate one using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

    # Admin User (Single Admin Mode)
    admin_username: str = Field(default="admin", validation_alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", validation_alias="ADMIN_PASSWORD")

    # MinIO (Object Storage)
    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", validation_alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")
    minio_bucket_name: str = Field(default="diting-datasets", validation_alias="MINIO_BUCKET_NAME")

    # LLM Configuration (for diting-core)
    default_llm_model: str = Field(default="gpt-4o-mini", validation_alias="DEFAULT_LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")
    llm_timeout: float = Field(default=60.0, validation_alias="LLM_TIMEOUT")

    # Embedding Configuration (for diting-core)
    default_embedding_model: str = Field(default="bge-m3", validation_alias="DEFAULT_EMBEDDING_MODEL")
    embedding_base_url: Optional[str] = Field(default=None, validation_alias="EMBEDDING_BASE_URL")
    embedding_api_key: Optional[str] = Field(default=None, validation_alias="EMBEDDING_API_KEY")
    embedding_timeout: float = Field(default=60.0, validation_alias="EMBEDDING_TIMEOUT")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["*"], validation_alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], validation_alias="CORS_ALLOW_HEADERS")

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    # Task Queue (arq)
    arq_redis_url: Optional[str] = Field(default=None, validation_alias="ARQ_REDIS_URL")

    @field_validator("arq_redis_url", mode="before")
    @classmethod
    def set_arq_redis_url(cls, v: Optional[str], info) -> str:
        """Set arq redis url from redis_url if not provided."""
        if v is not None:
            return v
        # Get redis_url from values
        redis_url = info.data.get("redis_url")
        return str(redis_url) if redis_url else "redis://localhost:6379/0"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        url = str(self.database_url)
        return url.replace("+asyncpg", "")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance.
    
    Returns:
        Settings instance
    """
    return settings
