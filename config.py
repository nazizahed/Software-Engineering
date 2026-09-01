"""Environment-based configuration shared by the API, ETL, and dashboard."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "se4geo")
    db_user: str = os.getenv("DB_USER", "se4geo")
    db_password: str | None = os.getenv("DB_PASSWORD") or None
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:5000/api").rstrip("/")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8050").split(",")
        if origin.strip()
    )
    flask_debug: bool = _as_bool(os.getenv("FLASK_DEBUG", "false"))


settings = Settings()


def database_connection_kwargs() -> dict[str, object]:
    """Return Psycopg connection arguments without embedding credentials in code."""
    values: dict[str, object] = {
        "host": settings.db_host,
        "port": settings.db_port,
        "dbname": settings.db_name,
        "user": settings.db_user,
    }
    if settings.db_password:
        values["password"] = settings.db_password
    return values

