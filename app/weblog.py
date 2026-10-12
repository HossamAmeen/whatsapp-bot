import logging
from pathlib import Path

SEPARATOR = "*" * 50

# Dedicated logger: only webhook requests and outgoing messages go through it
logger = logging.getLogger("whatsapp.webhook")
logger.setLevel(logging.INFO)
logger.propagate = False
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "webhook.log"
LOG_FILE.parent.mkdir(exist_ok=True)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(_handler)


def log_entry(message: str, *args) -> None:
    """Log one entry, followed by a 50-star separator."""
    logger.info(message + "\n" + SEPARATOR, *args)
