import httpx

from .config import settings

URL = f"https://graph.facebook.com/{settings.graph_version}/{settings.phone_number_id}/messages"
HEADERS = {"Authorization": f"Bearer {settings.whatsapp_token}"}


async def _call(body: dict) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            URL, headers=HEADERS, json={"messaging_product": "whatsapp", **body}
        )
    if res.is_error:
        print("WhatsApp API error:", res.status_code, res.text)


async def send_text(to: str, text: str) -> None:
    await _call({"to": to, "type": "text", "text": {"body": text}})


async def mark_read(message_id: str) -> None:
    await _call({"status": "read", "message_id": message_id})


async def send_buttons(to: str, text: str, buttons: list[tuple[str, str]]) -> None:
    """buttons: list of (id, title); WhatsApp allows at most 3."""
    await _call(
        {
            "to": to,
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
