import hashlib
import hmac
import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from .bot import handle_message
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("whatsapp")

app = FastAPI(title="WhatsApp Bot")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.middleware("http")
async def log_webhook_requests(request: Request, call_next):
    """Log method, URL, headers and body of every request to /webhook."""
    if request.url.path == "/webhook":
        body = await request.body()  # cached, so the endpoint can still read it
        logger.info(
            "%s %s\nheaders=%s\nbody=%s",
            request.method,
            request.url,
            json.dumps(dict(request.headers), indent=2),
            body.decode(errors="replace"),
        )
    return await call_next(request)


@app.get("/webhook")
async def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    """Meta calls this once when you save the webhook URL."""
    if mode == "subscribe" and token == settings.verify_token:
        return PlainTextResponse(challenge)
    raise HTTPException(403)


def _valid_signature(body: bytes, header: str) -> bool:
    if not settings.app_secret:  # skip in early dev
        return True
    expected = "sha256=" + hmac.new(settings.app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header, expected)


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    body = await request.body()
    if not _valid_signature(body, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401)

    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                background.add_task(handle_message, message)
    return {"status": "ok"}  # ack fast; messages are processed after the response
