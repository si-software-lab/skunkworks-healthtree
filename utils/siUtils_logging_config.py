import pathlib
import inspect


# derive name of caller
def caller():
    stack = inspect.stack()
    stack_length = len(stack)
    frame = stack[stack_length - 1]
    caller = pathlib.Path(frame.filename).name.split('.')[0]
    return caller


# derive project root from anywhere on this repo's filesystem tree
def repo_base_name(starting_path=None):
    p = pathlib.Path(starting_path or __file__).resolve()
    return next(parent for parent in [p] +list(p.parents) if (parent / '.git').exists())


# file sys name walk
caller = caller()
project_root = repo_base_name()
logging_dir = project_root / "logs"
logging_dir.mkdir(parents=True, exist_ok=True) # ensure logging directory exists


# cover letter logging config
logging_config_dict = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {
            "format": "-> %(filename)s - %(asctime)s - %(levelname)s </> %(message)s"
        },
        "detailed": {
            "format": "-> %(filename)s - %(asctime)s - %(name)s - %(levelname)s </>  %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO",  # Log at INFO level
            "formatter": "detailed",
            "filename": str(logging_dir / f"{caller}.log"),
            "mode": "a"
        },
    },
    "root": {
        "level": "INFO",  # Set root logger to INFO level
        "handlers": ["console", "file"],
    },
}

