import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.environ.get("PRIMEBOT_LOG_DIR", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "primebot.jsonl")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT = 5

os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("primebot")

if not any(isinstance(h, RotatingFileHandler) for h in _logger.handlers):
    _file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_file_handler)


def log_event(event: str, level: str = "info", **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    msg = json.dumps(payload, ensure_ascii=True, default=str)
    log_fn = getattr(_logger, level, _logger.info)
    log_fn(msg)
