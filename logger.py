import logging
import logging.handlers
from pathlib import Path
from config import get_settings


def setup_logger() -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger("docustream")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(settings.log_level)
    
    logs_dir = Path(settings.storage_path) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(logs_dir / "docustream.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(settings.log_level)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(settings.log_level)
    logger.addHandler(console_handler)
    
    logger.propagate = False
    
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("docustream")
