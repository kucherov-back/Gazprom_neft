"""Конфигурация логирования через dictConfig."""

from logging.config import dictConfig

from app.config import settings


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"level": settings.log_level, "handlers": ["console"]},
            "loggers": {
                "uvicorn.access": {"level": settings.log_level, "propagate": True},
            },
        }
    )
