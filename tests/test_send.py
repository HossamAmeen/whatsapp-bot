"""Manual check: sends a real WhatsApp message. Run from the project root:

    .venv/bin/python -m tests.test_send
"""
import asyncio

from app.whatsapp import send_text

TEST_NUMBER = "201010079798"  # +201010079798, WhatsApp format (digits, no "+")


async def test_send_message() -> None:
    await send_text(TEST_NUMBER, "Test message from Ti Soft bot ✅")


if __name__ == "__main__":
    asyncio.run(test_send_message())
