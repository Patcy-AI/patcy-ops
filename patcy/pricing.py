"""
pricing.py — build a real, itemized quote from the service catalog. Deterministic math, so pricing
is never hallucinated by the model — the agent decides WHICH service and quantity; this computes the money.
"""
from .config import SERVICES


def build_quote(sku: str, quantity: float, add_mobilization: int = 1, discount_pct: float = 0.0):
    """Return an itemized quote dict for a service SKU.
    quantity = hours (hourly), units (unit), or 1 (fixed). add_mobilization = number of trips."""
    svc = SERVICES.get(sku)
    if not svc:
        raise ValueError(f"Unknown service SKU: {sku}")
    items = []
    qty = float(quantity or 1)
    line_total = round(svc["rate"] * qty, 2)
    unit_label = {"hourly": "hr", "unit": svc.get("unit", "unit"), "fixed": "job"}[svc["rate_type"]]
    items.append({"sku": sku, "description": svc["name"], "qty": qty, "unit": unit_label,
                  "rate": svc["rate"], "amount": line_total})

    if add_mobilization:
        mob = SERVICES["MOB"]
        mob_total = round(mob["rate"] * add_mobilization, 2)
        items.append({"sku": "MOB", "description": mob["name"], "qty": add_mobilization,
                      "unit": "trip", "rate": mob["rate"], "amount": mob_total})

    subtotal = round(sum(i["amount"] for i in items), 2)
    discount = round(subtotal * (discount_pct / 100.0), 2)
    total = round(subtotal - discount, 2)
    return {"sku": sku, "service": svc["name"], "template": svc["template"], "scope": svc["scope"],
            "items": items, "subtotal": subtotal, "discount": discount,
            "discount_pct": discount_pct, "total": total, "rate_type": svc["rate_type"]}


def money(v) -> str:
    return "${:,.2f}".format(float(v))
