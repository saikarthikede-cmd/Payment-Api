import logging
from logging.config import dictConfig

from app.config import settings


def setup_logging() -> None:
    log_level = settings.log_level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": log_level,
            },
        }
    )
    logging.getLogger(__name__).info("Logging configured with level=%s", log_level)
