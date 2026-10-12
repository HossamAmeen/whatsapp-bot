import json

import httpx

from .config import settings
from .weblog import log_entry

URL = f"https://graph.facebook.com/{settings.graph_version}/{settings.phone_number_id}/messages"
HEADERS = {"Authorization": f"Bearer {settings.whatsapp_token}"}


def _recipient(to: str) -> dict:
    # Phone numbers are digits only; business-scoped user IDs look like "EG.1683..."
    return {"to": to} if to.isdigit() else {"recipient": to}


async def _call(body: dict) -> None:
    payload = {"messaging_product": "whatsapp", **body}
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(URL, headers=HEADERS, json=payload)
    log_entry(
        "SENT POST %s\nbody=%s\nresponse=%s %s",
        URL,
        json.dumps(payload, ensure_ascii=False),
        res.status_code,
        res.text,
    )


async def send_text(to: str, text: str) -> None:
    await _call({**_recipient(to), "type": "text", "text": {"body": text}})


async def mark_read(message_id: str) -> None:
    await _call({"status": "read", "message_id": message_id})


async def send_buttons(to: str, text: str, buttons: list[tuple[str, str]]) -> None:
    """buttons: list of (id, title); WhatsApp allows at most 3."""
    await _call(
        {
            **_recipient(to),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": i, "title": t[:20]}}
                        for i, t in buttons[:3]
                    ]
                },
            },
        }
    )
