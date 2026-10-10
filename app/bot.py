from .whatsapp import mark_read, send_buttons, send_text


async def handle_message(message: dict) -> None:
    """Put your bot logic here. `message` is the raw WhatsApp message object."""
    sender = message["from"]
    await mark_read(message["id"])

    kind = message.get("type")
    if kind == "text":
        user_input = message["text"]["body"].strip().lower()
    elif kind == "interactive":
        reply = message["interactive"].get("button_reply") or message["interactive"].get("list_reply") or {}
        user_input = reply.get("id", "")
    else:
        await send_text(sender, "Sorry, I only understand text for now.")
        return

    if user_input == "hours":
        await send_text(sender, "We're open 9am–5pm, Sun–Thu.")
    elif user_input == "support":
        await send_text(sender, "A team member will contact you soon.")
    else:
        await send_buttons(
            sender,
            "Hi! How can I help you?",
            [("hours", "Opening hours"), ("support", "Talk to support")],
        )
