thonimport logging
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "automation_bot"
_CONFIGURED = False

def _find_project_root(start: Optional[Path] = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config").is_dir() and (parent / "src").is_dir():
            return parent
    # Fallback to two levels up (src/automation/utils -> src/automation -> src -> root)
    return current.parent.parent.parent

def _configure_logger() -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    if _CONFIGURED:
        return logger

    logger.setLevel(logging.INFO)

    project_root = _find_project_root()
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "activity.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    _CONFIGURED = True
    logger.debug("Logger configured; logging to %s", log_file)
    return logger

def get_logger() -> logging.Logger:
    if not _CONFIGURED:
        return _configure_logger()
    return logging.getLogger(_LOGGER_NAME)