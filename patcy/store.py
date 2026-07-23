"""
store.py — Patcy Ops's memory. A simple JSON datastore for projects, proposals, invoices, tasks and
the schedule, with the date/status fields the Follow-up agent needs. In production this is the CRM +
QuickBooks; the interface is the same.
"""
import datetime as _dt
import json
import os

DB_PATH = os.environ.get("PATCY_DB", os.path.join(os.path.dirname(__file__), "..", "patcy_db.json"))

_EMPTY = {"projects": [], "proposals": [], "invoices": [], "tasks": [], "schedule": [], "log": [],
          "approvals": [],
          "counters": {"PRO": 140, "INV": 300, "TR1": 70, "PRJ": 20, "TASK": 0, "APR": 0}}


def load():
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return json.loads(json.dumps(_EMPTY))


def save(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def reset():
    save(json.loads(json.dumps(_EMPTY)))


def seed_demo(today=None):
    """Populate a realistic prior state so the Payment agent has an invoice to mark paid and the
    Follow-up agent has an overdue invoice + an expiring proposal to chase."""
    today = today or _dt.date.today()
    db = json.loads(json.dumps(_EMPTY))
    db["invoices"] = [
        {"ref": "INV-2026-0298", "customer_name": "Brightline Contracting", "amount": 4200.0,
         "status": "sent", "due_date": (today + _dt.timedelta(days=18)).isoformat(), "project": "88 Jay St Facade"},
        {"ref": "INV-2026-0291", "customer_name": "Hudson Yards Builders", "amount": 8900.0,
         "status": "sent", "due_date": (today - _dt.timedelta(days=12)).isoformat(), "project": "20 Hudson Yards Steel"},
    ]
    db["proposals"] = [
        {"ref": "PRO-2026-0138", "customer_name": "Acme Development LLC", "amount": 12000.0,
         "status": "sent", "expires": (today + _dt.timedelta(days=3)).isoformat(), "project": "Acme Tower Phase 1"},
    ]
    save(db)
    return db


def next_ref(db, kind):
    db["counters"][kind] = db["counters"].get(kind, 0) + 1
    year = 2026
    return f"{kind}-{year}-{db['counters'][kind]:04d}"


def log(db, agent, message):
    db["log"].append({"agent": agent, "message": message})


def add(db, table, record):
    db[table].append(record)
    return record


def find_followups(db, today=None):
    """Return reminders the Follow-up agent should send: overdue invoices + expiring proposals."""
    today = today or _dt.date.today()
    out = []
    for inv in db["invoices"]:
        if inv.get("status") == "sent" and inv.get("due_date"):
            due = _dt.date.fromisoformat(inv["due_date"])
            if due < today:
                out.append({"type": "overdue_invoice", "ref": inv["ref"], "customer": inv["customer_name"],
                            "amount": inv["amount"], "days": (today - due).days})
    for pro in db["proposals"]:
        if pro.get("status") == "sent" and pro.get("expires"):
            exp = _dt.date.fromisoformat(pro["expires"])
            if 0 <= (exp - today).days <= 5:
                out.append({"type": "expiring_proposal", "ref": pro["ref"], "customer": pro["customer_name"],
                            "amount": pro["amount"], "days": (exp - today).days})
    return out
