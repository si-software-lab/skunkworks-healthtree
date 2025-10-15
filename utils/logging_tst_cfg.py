# utils/logging_config.py

from pathlib import Path

project_root = Path(__file__).resolve().parents[1]  # adjust if needed
logs_dir = project_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logging_config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "std": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "std",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "std",
            "filename": str(logs_dir / "app.log"),  # script can override if desired
            "mode": "a",
            "maxBytes": 5_000_000,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        # your script logger name; your code uses f"{stem}-logger"
        # this ensures it picks up both handlers
        "demo": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "WARNING"
    },
}