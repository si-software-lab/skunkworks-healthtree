# loader/config.py
import os
import logging

def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_env_var(name: str, default=None):
    return os.getenv(name, default)

def get_int_env_var(name: str, default=0):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default