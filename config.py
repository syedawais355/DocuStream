from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    api_key: str = "change-me-to-at-least-32-chars-long"
    storage_dir: str = "./data"
    max_file_size_mb: int = 50
    max_concurrent_tasks: int = 4
    max_queue_length: int = 100
    job_ttl_seconds: int = 3600
    log_level: str = "INFO"
    soffice_path: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
