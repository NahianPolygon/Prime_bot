import json
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("primebot")


def log_event(event: str, level: str = "info", **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    msg = json.dumps(payload, ensure_ascii=True, default=str)
    log_fn = getattr(_logger, level, _logger.info)
    log_fn(msg)
