import logging

from .whatsapp import send_text

logger = logging.getLogger("whatsapp.webhook")

# Testing only: reply just to these numbers (WhatsApp format: digits, no "+")
ALLOWED_NUMBERS = {"201010079798"}


async def handle_message(message: dict) -> None:
    """Put your bot logic here. `message` is the raw WhatsApp message object."""
    sender = message["from"]
    text = message.get("text", {}).get("body", "")
    logger.info("message from=%s type=%s text=%r", sender, message.get("type"), text)

    if sender not in ALLOWED_NUMBERS:
        return
    await send_text(sender, "Thank you for contacting us")
