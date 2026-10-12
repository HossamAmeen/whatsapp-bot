import logging

from . import store
from .catalog import CATEGORIES, OFFERS, PRODUCTS, products_in
from .whatsapp import send_text

logger = logging.getLogger("whatsapp.webhook")

# In-memory sessions (reset on restart): sender -> {"state", "cart", "mode", ...}
SESSIONS: dict[str, dict] = {}

NEW_CUSTOMER_FIELDS = [
    "اسم العميل / اسم النشاط",
    "اسم المسؤول",
    "رقم الهاتف",
    "نوع النشاط",
    "المحافظة",
    "المنطقة",
    "العنوان",
    "الموقع (Location) - أرسل موقعك أو اكتب العنوان",
    "البيانات التجارية / الضريبية (اكتب - للتخطي)",
]
EXISTING_CUSTOMER_FIELDS = [
    "رقم الهاتف",
    "اسم العميل / المسؤول",
    "اسم المحل / الكشك / النشاط",
    "المحافظة",
    "المنطقة",
    "العنوان",
    "الموقع (Location) - أرسل موقعك أو اكتب العنوان",
    "كود العميل إن وجد (اكتب - للتخطي)",
]
COMPLAINT_TYPES = {
    "1": "مشكلة في المنتج",
    "2": "نقص في الكمية",
    "3": "منتج تالف",
    "4": "مشكلة في التوصيل",
    "5": "مشكلة في الفاتورة",
    "6": "أخرى",
}

MAIN_MENU = (
    "أهلاً بك في Ti Soft 👋\n"
    "اختر من القائمة:\n\n"
    "1️⃣ المبيعات والطلبات\n"
    "2️⃣ الشكاوى والمقترحات\n"
    "3️⃣ التحدث مع خدمة العملاء\n\n"
    "اكتب 0 في أي وقت للعودة للقائمة الرئيسية"
)
SALES_MENU = (
    "قائمة المبيعات:\n\n"
    "1️⃣ عرض المنتجات\n"
    "2️⃣ العروض الحالية\n"
    "3️⃣ طلب عرض سعر\n"
    "4️⃣ عمل أوردر\n"
    "5️⃣ متابعة الأوردر\n"
    "6️⃣ التحدث مع خدمة العملاء\n"
    "0️⃣ القائمة الرئيسية"
)
STANDARD_OPTIONS = "1️⃣ العودة للقائمة الرئيسية\n2️⃣ إنهاء المحادثة\n3️⃣ التحدث مع خدمة العملاء"
HANDOFF = "تم تحويلك إلى خدمة العملاء، سيتواصل معك أحد ممثلينا قريباً 👩‍💼\n(اكتب 0 للعودة للقائمة الرئيسية)"
END = "شكراً لتواصلك مع Ti Soft 🌷 نتشرف بخدمتك دائماً."


def _input(message: dict) -> str:
    """Normalize any incoming message type to a text value."""
    t = message.get("type")
    if t == "text":
        return message["text"]["body"].strip()
    if t == "interactive":
        i = message["interactive"]
        return (i.get("button_reply") or i.get("list_reply") or {}).get("id", "")
    if t == "location":
        loc = message["location"]
        return f"https://maps.google.com/?q={loc['latitude']},{loc['longitude']}"
    if t in ("image", "video", "document"):
        m = message[t]
        return f"[{t}:{m.get('id')}] {m.get('caption', '')}".strip()
    return ""


def _cart_text(cart: list[dict]) -> tuple[str, float]:
    lines, total = [], 0.0
    for n, it in enumerate(cart, 1):
        sub = it["qty"] * it["price"]
        total += sub
        lines.append(f"{n}. {it['name']} × {it['qty']} — {it['price']:g} = {sub:g}")
    return "\n".join(lines), total


def _product_card(pid: str) -> str:
    p = PRODUCTS[pid]
    return (
        f"📦 {p['name']}\nالمواصفات: {p['specs']}\nالتعبئة: {p['pack']}\nالسعر: {p['price']:g} ج.م"
    )


def _categories_text() -> str:
    return "اختر القسم:\n\n" + "\n".join(f"{k}️⃣ {v}" for k, v in CATEGORIES.items()) + "\n0️⃣ القائمة الرئيسية"


def _list_products(s: dict, cat: str) -> str:
    items = products_in(cat)
    if not items:
        return "لا توجد منتجات في هذا القسم حالياً.\n\n" + _categories_text()
    s["state"] = "product_list"
    s["list"] = [pid for pid, _ in items]
    body = "\n".join(f"{n}. {p['name']} — {p['price']:g} ج.م" for n, (_, p) in enumerate(items, 1))
    return f"{CATEGORIES[cat]}:\n\n{body}\n\nاكتب رقم المنتج، أو 9 للرجوع للأقسام"


def _to_main(s: dict) -> str:
    s.clear()
    s["state"] = "main"
    return MAIN_MENU


def _to_sales(s: dict) -> str:
    s["state"] = "sales_menu"
    return SALES_MENU


def _handoff(s: dict, sender: str, reason: str) -> str:
    store.save("handoffs", {"wa": sender, "reason": reason})
    s["state"] = "human"
    return HANDOFF


def _start_form(s: dict, kind: str) -> str:
    s["state"] = "form"
    s["form"] = {"kind": kind, "step": 0, "answers": {}}
    fields = NEW_CUSTOMER_FIELDS if kind == "new" else EXISTING_CUSTOMER_FIELDS
    return f"من فضلك أدخل البيانات التالية:\n\n1/{len(fields)} {fields[0]}"


def _shop_menu(s: dict) -> str:
    s["state"] = "shop_catalog"
    return _categories_text()


def _cart_review(s: dict) -> str:
    text, total = _cart_text(s["cart"])
    if s["mode"] == "order":
        s["state"] = "order_confirm"
        return f"🛒 سلة الطلب:\n{text}\n\nالإجمالي: {total:g} ج.م\n\n1️⃣ تأكيد الطلب\n2️⃣ تعديل الأوردر\n3️⃣ إلغاء الأوردر"
    s["state"] = "quote_notes"
    return f"💰 المنتجات المطلوبة:\n{text}\n\nأضف ملاحظاتك على الطلب (اكتب - للتخطي)"


async def _reply(sender: str, s: dict, text: str, message: dict) -> str:
    state = s.get("state", "main")

    if text == "0" or state == "main" and text not in ("1", "2", "3"):
        return _to_main(s)

    # ---- main menu ----
    if state == "main":
        if text == "1":
            s["state"] = "customer_type"
            return "نوع العميل:\n\n1️⃣ عميل جديد\n2️⃣ عميل متعامل مع Ti Soft\n0️⃣ القائمة الرئيسية"
        if text == "2":
            s["state"] = "complaint_type"
            return "نوع الشكوى:\n\n" + "\n".join(f"{k}️⃣ {v}" for k, v in COMPLAINT_TYPES.items()) + "\n0️⃣ القائمة الرئيسية"
        return _handoff(s, sender, "main menu")

    if state == "human":
        return ""  # an agent has the conversation; stay silent until the customer sends 0

    # ---- customer type / forms ----
    if state == "customer_type":
        if text == "1":
            return _start_form(s, "new")
        if text == "2":
            known = store.find_customer(sender)
            if known:
                s["customer"] = known
                return f"أهلاً {known.get('name', '')} 🌟\n\n" + _to_sales(s)
            return _start_form(s, "existing")
        return "من فضلك اختر 1 أو 2 (أو 0 للقائمة الرئيسية)"

    if state == "form":
        f = s["form"]
        fields = NEW_CUSTOMER_FIELDS if f["kind"] == "new" else EXISTING_CUSTOMER_FIELDS
        f["answers"][fields[f["step"]]] = "" if text == "-" else text
        f["step"] += 1
        if f["step"] < len(fields):
            return f"{f['step'] + 1}/{len(fields)} {fields[f['step']]}"
        a = list(f["answers"].values())
        record = {"kind": f["kind"], "wa": sender, "answers": f["answers"]}
        record["phone"], record["name"] = (a[2], a[0]) if f["kind"] == "new" else (a[0], a[1])
        store.save("customers", record)
        s["customer"] = record
        if f["kind"] == "new":
            return "✅ تم تسجيل بياناتك بنجاح.\n\n" + _to_sales(s)
        return "✅ استلمنا بياناتك وسيتم البحث عن حسابك بواسطة خدمة العملاء.\n\n" + _to_sales(s)

    # ---- sales menu ----
    if state == "sales_menu":
        if text == "1":
            s["mode"] = "browse"
            return _shop_menu(s)
        if text == "2":
            if not OFFERS:
                return "لا توجد عروض حالية.\n\n" + SALES_MENU
            s["state"] = "offers"
            s["list"] = [o["product"] for o in OFFERS]
            body = "\n\n".join(
                f"🔥 {n}. {PRODUCTS[o['product']]['name']}\nالسعر: {o['price']:g} ج.م\n{o['details']}\nالمدة: {o['duration']}"
                for n, o in enumerate(OFFERS, 1)
            )
            return f"العروض الحالية:\n\n{body}\n\nاكتب رقم العرض لإضافته للأوردر\n{STANDARD_OPTIONS}"
        if text in ("3", "4"):
            s["mode"] = "quote" if text == "3" else "order"
            s["cart"] = []
            return _shop_menu(s)
        if text == "5":
            return _handoff(s, sender, "order tracking")
        if text == "6":
            return _handoff(s, sender, "sales menu")
        return SALES_MENU

    # ---- catalog browsing / cart building ----
    if state == "shop_catalog":
        if text in CATEGORIES:
            return _list_products(s, text)
        return _categories_text()

    if state == "product_list":
        if text == "9":
            return _shop_menu(s)
        if text.isdigit() and 1 <= int(text) <= len(s["list"]):
            s["pid"] = s["list"][int(text) - 1]
            if s["mode"] == "browse":
                s["state"] = "product_options"
                return (
                    f"{_product_card(s['pid'])}\n\n1️⃣ إضافة للأوردر\n2️⃣ العودة للمنتجات\n"
                    "3️⃣ العودة للقائمة الرئيسية\n4️⃣ إنهاء المحادثة\n5️⃣ التحدث مع خدمة العملاء"
                )
            s["state"] = "qty"
            return f"{_product_card(s['pid'])}\n\nاكتب الكمية المطلوبة (عدد الكراتين):"
        return "من فضلك اكتب رقم المنتج من القائمة، أو 9 للرجوع"

    if state == "product_options":
        if text == "1":
            s["mode"] = "order"
            s.setdefault("cart", [])
            s["state"] = "qty"
            return "اكتب الكمية المطلوبة (عدد الكراتين):"
        if text == "2":
            return _shop_menu(s)
        if text == "4":
            return _end(s)
        if text == "5":
            return _handoff(s, sender, "product options")
        return "من فضلك اختر رقماً من 1 إلى 5 (أو 0 للقائمة الرئيسية)"

    if state == "offers":
        if text.isdigit() and 1 <= int(text) <= len(s["list"]):
            s["pid"] = s["list"][int(text) - 1]
            s["price_override"] = OFFERS[int(text) - 1]["price"]
            s["mode"] = "order"
            s.setdefault("cart", [])
            s["state"] = "qty"
            return "اكتب الكمية المطلوبة (عدد الكراتين):"
        if text == "1":
            return _to_main(s)
        if text == "2":
            return _end(s)
        if text == "3":
            return _handoff(s, sender, "offers")
        return "من فضلك اختر رقم العرض أو أحد الخيارات:\n" + STANDARD_OPTIONS

    if state == "qty":
        if not (text.isdigit() and int(text) > 0):
            return "من فضلك اكتب كمية صحيحة (رقم أكبر من صفر)"
        p = PRODUCTS[s["pid"]]
        price = s.pop("price_override", p["price"])
        s["cart"].append({"pid": s["pid"], "name": p["name"], "qty": int(text), "price": price})
        s["state"] = "after_add"
        verb = "إتمام الطلب" if s["mode"] == "order" else "إرسال طلب عرض السعر"
        return f"✅ تمت الإضافة.\n\n1️⃣ إضافة منتج آخر\n2️⃣ {verb}\n0️⃣ القائمة الرئيسية"

    if state == "after_add":
        if text == "1":
            return _shop_menu(s)
        if text == "2":
            return _cart_review(s)
        return "من فضلك اختر 1 أو 2 (أو 0 للقائمة الرئيسية)"

    # ---- order ----
    if state == "order_confirm":
        if text == "1":
            _, total = _cart_text(s["cart"])
            ref = store.save("orders", {"wa": sender, "customer": s.get("customer"), "items": s["cart"], "total": total})
            s["cart"] = []
            s["state"] = "done"
            return f"✅ تم إنشاء الأوردر رقم {ref}\nالإجمالي: {total:g} ج.م\nسيتم التواصل معك لتأكيد التسليم.\n\n{STANDARD_OPTIONS}"
        if text == "2":
            s["cart"] = []
            return "تم تفريغ السلة، اختر المنتجات من جديد:\n\n" + _shop_menu(s)
        if text == "3":
            s["cart"] = []
            s["state"] = "done"
            return f"تم إلغاء الأوردر.\n\n{STANDARD_OPTIONS}"
        return "من فضلك اختر 1 أو 2 أو 3"

    # ---- quotation ----
    if state == "quote_notes":
        ref = store.save(
            "quotations",
            {"wa": sender, "customer": s.get("customer"), "items": s["cart"], "notes": "" if text == "-" else text},
        )
        s["cart"] = []
        s["state"] = "done"
        return f"✅ تم استلام طلب عرض السعر رقم {ref}\nسيتم مراجعته من فريق المبيعات وإرسال العرض لك.\n\n{STANDARD_OPTIONS}"

    # ---- complaints ----
    if state == "complaint_type":
        if text in COMPLAINT_TYPES:
            s["complaint"] = {"type": COMPLAINT_TYPES[text], "details": []}
            s["state"] = "complaint_details"
            return "من فضلك اكتب تفاصيل المشكلة (رقم الأوردر إن وجد، وصف المشكلة) ويمكنك إرسال صور أو فيديو.\nعند الانتهاء اكتب: تم"
        return "من فضلك اختر رقماً من 1 إلى 6 (أو 0 للقائمة الرئيسية)"

    if state == "complaint_details":
        if text in ("تم", "done"):
            c = s["complaint"]
            if not c["details"]:
                return "من فضلك اكتب تفاصيل المشكلة أولاً"
            ref = store.save("complaints", {"wa": sender, "customer": s.get("customer"), **c})
            s["state"] = "done"
            return f"✅ تم تسجيل الشكوى رقم {ref}\nسيتواصل معك فريق خدمة العملاء قريباً.\n\n{STANDARD_OPTIONS}"
        s["complaint"]["details"].append(text)
        return "تم الاستلام ✅ أضف المزيد أو اكتب: تم"

    # ---- generic end-of-flow options ----
    if state == "done":
        if text == "1":
            return _to_main(s)
        if text == "2":
            return _end(s)
        if text == "3":
            return _handoff(s, sender, "after flow")
        return STANDARD_OPTIONS

    return _to_main(s)


def _end(s: dict) -> str:
    s.clear()
    s["state"] = "main"
    return END + "\n(اكتب أي رسالة لبدء محادثة جديدة)"


async def handle_message(message: dict) -> None:
    sender = message.get("from") or message["from_user_id"]
    text = _input(message)
    logger.info("message from=%s type=%s text=%r", sender, message.get("type"), text)

    s = SESSIONS.setdefault(sender, {"state": "new"})
    if s["state"] == "new":  # first contact: show the menu whatever they wrote
        s["state"] = "main"
        reply = MAIN_MENU
    else:
        reply = await _reply(sender, s, text, message)
    if reply:
        await send_text(sender, reply)
