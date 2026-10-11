"""Append-only JSONL storage for registrations, orders, quotations, complaints, handoffs."""
import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PREFIX = {"orders": "ORD", "quotations": "QUO", "complaints": "CMP"}


def _path(kind: str) -> Path:
    return DATA_DIR / f"{kind}.jsonl"


def load(kind: str) -> list[dict]:
    p = _path(kind)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]


def save(kind: str, record: dict) -> str:
    """Store a record and return its reference number (e.g. ORD-1001)."""
    ref = f"{PREFIX.get(kind, kind[:3].upper())}-{1001 + len(load(kind))}"
    record = {"ref": ref, "ts": int(time.time()), **record}
    with _path(kind).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return ref


def find_customer(phone: str) -> dict | None:
    for c in reversed(load("customers")):
        if c.get("phone") == phone or c.get("wa") == phone:
            return c
    return None
