from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = getenv("HCA_API_HOST", "127.0.0.1")
    port: int = int(getenv("HCA_API_PORT", "8000"))
    log_level: str = getenv("HCA_LOG_LEVEL", "info")
    max_upload_bytes: int = int(getenv("HCA_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


settings = Settings()
