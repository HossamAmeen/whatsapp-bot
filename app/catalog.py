"""Placeholder catalog and offers. Replace with real data (or a DB / admin panel later)."""

CATEGORIES = {
    "1": "مناديل الوجه",
    "2": "مناديل المطبخ",
    "3": "مناديل التواليت",
    "4": "منتجات أخرى",
    "5": "المنتجات الجديدة",
}

# id -> product. `category` is a key of CATEGORIES (new products also list under "5" via `new`).
PRODUCTS = {
    "F1": {"category": "1", "name": "مناديل وجه 100 منديل", "specs": "طبقتين - ناعمة", "pack": "كرتونة 48 علبة", "price": 480.0},
    "F2": {"category": "1", "name": "مناديل وجه 200 منديل", "specs": "طبقتين - ناعمة", "pack": "كرتونة 36 علبة", "price": 620.0},
    "K1": {"category": "2", "name": "مناديل مطبخ رول", "specs": "رول كبير - ماص", "pack": "كرتونة 12 رول", "price": 300.0},
    "T1": {"category": "3", "name": "تواليت 10 رولات", "specs": "طبقتين", "pack": "كرتونة 8 عبوات", "price": 520.0},
    "O1": {"category": "4", "name": "مناديل جيب", "specs": "3 طبقات", "pack": "كرتونة 120 عبوة", "price": 360.0},
    "N1": {"category": "5", "name": "مناديل وجه بالألوفيرا", "specs": "طبقتين - معطرة", "pack": "كرتونة 36 علبة", "price": 700.0, "new": True},
}

OFFERS = [
    {"product": "F1", "price": 430.0, "details": "خصم على الكرتونة عند طلب 10 كراتين أو أكثر", "duration": "حتى نهاية الشهر"},
]


def products_in(category: str) -> list[tuple[str, dict]]:
    return [(pid, p) for pid, p in PRODUCTS.items() if p["category"] == category]
