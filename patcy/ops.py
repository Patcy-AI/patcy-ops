"""
ops.py — the multi-agent orchestrator: the "supervisor" that reads each email, decides which
specialist agent handles it, and runs the real action (generate a proposal PDF, schedule an
inspector, create an invoice, fill a TR1, log a payment, or answer a question).

Classification + field extraction are rule-based so the whole pipeline runs offline and
deterministically (great for a live demo). When an LLM key is present, `draft_reply` uses it to
write nicer client emails; the money and the documents never depend on the model.
"""
import datetime as _dt
import re
import urllib.parse

from . import store
from .config import COMPANY, CUSTOMERS, STAFF, find_service
from .documents import generate_invoice, generate_proposal, generate_tr1
from .pricing import build_quote, money

SERVICE_CERT = {"SI-CONC": "Concrete", "SI-STRUCT": "Structural Steel", "SO-OBS": "Structural Observation",
                "FP-INSP": "Firestopping", "ENG-SVC": "TR1"}


# ---------------------------------------------------------------------------
# Intake agent — classify + extract
# ---------------------------------------------------------------------------
def classify(email: dict) -> dict:
    text = (email.get("subject", "") + " " + email.get("body", "")).lower()
    strong_proposal = any(p in text for p in [
        "send a proposal", "send me a proposal", "send us a proposal", "need a proposal",
        "send a quote", "send me a quote", "proposal request", "please quote", "can you send a proposal"])
    is_question = any(p in text for p in [
        "quick question", "just a question", "does your firm", "do you provide", "do you offer",
        "what's the typical", "what is the typical", "just wondering"])
    if re.search(r"\b(payment|paid|ach|remitt|wire transfer)\b", text) and "invoice" in text:
        cat = "payment"
    elif "tr1" in text or "tr8" in text or ("technical report" in text) or ("dob" in text and "file" in text):
        cat = "tr1_request"
    elif re.search(r"\b(schedule|inspector on site|erection|book|send someone)\b", text) and \
            re.search(r"\b(inspect|inspection|steel|welding)\b", text):
        cat = "inspection_request"
    elif strong_proposal:
        cat = "proposal_request"
    elif is_question:
        cat = "question"
    elif re.search(r"\b(proposal|quote|estimate|pricing|how much)\b", text):
        cat = "proposal_request"
    else:
        cat = "question"
    return {"category": cat, "sku": find_service(text), "hours": _extract_hours(text),
            "dob": _extract_dob(email.get("body", ""))}


def _extract_hours(text):
    m = re.search(r"(\d+)\s*(?:hours|hrs)", text)
    return int(m.group(1)) if m else 24


def _extract_dob(body):
    job = re.search(r"\b([MBKQ]\d{7,9})\b", body)
    bl = re.search(r"[Bb]lock\s*(\d+)\s*[,/ ]*\s*[Ll]ot\s*(\d+)", body)
    bin_ = re.search(r"\bBIN\s*(\d{6,8})\b", body)
    return {"job_no": job.group(1) if job else "", "block_lot": f"{bl.group(1)} / {bl.group(2)}" if bl else "",
            "bin": bin_.group(1) if bin_ else ""}


def _customer(email):
    key = email.get("customer_key")
    if key and key in CUSTOMERS:
        return dict(CUSTOMERS[key])
    frm = email.get("from", "Unknown <unknown@example.com>")
    name = frm.split("<")[0].strip() or "Prospective Client"
    mail = re.search(r"<(.+?)>", frm)
    return {"name": name, "contact": name, "email": mail.group(1) if mail else "", "address": ""}


def _project(email, cust):
    body = email.get("body", "")
    addr = re.search(r"\bat ([\w .,#-]+?(?:Ave|St|Street|Avenue|Blvd|Road|Rd|Yards)[\w .,#]*)", body)
    borough = next((b for b in ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"] if b in body), "Manhattan")
    name = re.sub(r"^(re:|fwd:)\s*", "", email.get("subject", "Project"), flags=re.I)
    return {"name": name[:60], "address": addr.group(1).strip() if addr else cust.get("address", ""),
            "borough": borough}


def assign_inspector(sku, borough):
    cert = SERVICE_CERT.get(sku, "Concrete")
    for s in STAFF:
        if cert in s["certs"] and (borough in s["boroughs"] or "All" in s["boroughs"]):
            return s
    for s in STAFF:                       # fallback: cert match, any borough
        if cert in s["certs"]:
            return s
    return STAFF[0]


def _gcal_link(title, date, time, minutes, details=""):
    start = _dt.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end = start + _dt.timedelta(minutes=minutes)
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(
        {"action": "TEMPLATE", "text": title, "dates": start.strftime("%Y%m%dT%H%M%S") + "/" +
         end.strftime("%Y%m%dT%H%M%S"), "details": details})


# ---------------------------------------------------------------------------
# The supervisor: route one email to the right specialist agent + do the work
# ---------------------------------------------------------------------------
def process_email(db, email, today=None):
    today = today or _dt.date.today()
    info = classify(email)
    cust = _customer(email)
    proj = _project(email, cust)
    result = {"email_id": email["id"], "from": email["from"], "subject": email["subject"],
              "category": info["category"], "actions": [], "artifacts": [], "tasks": []}

    def act(agent, msg):
        store.log(db, agent, msg)
        result["actions"].append({"agent": agent, "msg": msg})

    def task(agent, desc, owner=""):
        ref = store.next_ref(db, "TASK")
        store.add(db, "tasks", {"ref": ref, "task": desc, "owner": owner, "agent": agent,
                                "customer": cust["name"], "status": "open"})
        result["tasks"].append({"task": desc, "owner": owner})

    act("Intake", f"Classified email from {cust['name']} as '{info['category']}'.")

    if info["category"] == "proposal_request":
        q = build_quote(info["sku"], info["hours"], add_mobilization=max(2, info["hours"] // 8))
        ref = store.next_ref(db, "PRO")
        path = generate_proposal({"ref": ref, "customer": cust, "project": proj, "quote": q})
        store.add(db, "proposals", {"ref": ref, "customer_name": cust["name"], "amount": q["total"],
                                    "status": "sent", "expires": (today + _dt.timedelta(
                                        days=COMPANY["proposal_valid_days"])).isoformat(), "project": proj["name"]})
        act("Proposal", f"Generated {q['template']} {ref} for {cust['name']} — {money(q['total'])}.")
        act("Proposal", f"Drafted client email to {cust['email']} with the proposal attached.")
        task("Proposal", f"Send proposal {ref} to {cust['email']} and log follow-up", "Ops")
        result["artifacts"].append({"kind": "Proposal", "ref": ref, "path": path, "amount": q["total"]})

    elif info["category"] == "inspection_request":
        insp = assign_inspector(info["sku"], proj["borough"])
        date = (today + _dt.timedelta(days=3)).isoformat()
        link = _gcal_link(f"Special Inspection — {proj['name']}", date, "09:00", 180,
                          f"Inspector: {insp['name']} · {proj['address']}")
        store.add(db, "schedule", {"project": proj["name"], "inspector": insp["name"], "date": date,
                                   "time": "09:00", "type": SERVICE_CERT.get(info["sku"]), "link": link})
        act("Scheduling", f"Assigned {insp['name']} ({insp['role']}) for {SERVICE_CERT.get(info['sku'])} "
                          f"inspection in {proj['borough']} on {date} 9:00 AM.")
        act("Scheduling", f"Created calendar event and drafted confirmations to {cust['email']} and {insp['email']}.")
        task("Scheduling", f"Confirm inspection slot with {cust['name']} for {date}", insp["name"])
        result["artifacts"].append({"kind": "Calendar", "ref": date, "link": link})

    elif info["category"] == "payment":
        inv_ref = (re.search(r"INV-\d{4}-\d{4}", email["body"]) or [None])
        inv_ref = inv_ref.group(0) if hasattr(inv_ref, "group") else None
        act("Payment", f"Detected payment notification for {inv_ref or 'an invoice'} from {cust['name']}.")
        marked = False
        for inv in db["invoices"]:
            if inv["ref"] == inv_ref:
                inv["status"] = "paid"
                marked = True
        act("Payment", f"Marked {inv_ref} as PAID and updated project status." if marked
            else f"No matching invoice on file for {inv_ref}; flagged accounting to verify in QuickBooks.")
        task("Payment", f"Verify {inv_ref or 'payment'} cleared in QuickBooks and email receipt", "Accounting")

    elif info["category"] == "tr1_request":
        ref = store.next_ref(db, "TR1")
        path = generate_tr1({"ref": ref, "customer": cust, "project": proj,
                             "inspections": ["Concrete — cast-in-place (BC 1705.3)",
                                             "Firestopping (BC 1705.17)", "Structural Steel (BC 1705.2)"],
                             "inspector": assign_inspector(info["sku"], proj["borough"]), "dob": info["dob"]})
        act("DOB/Forms", f"Prepared TR1 technical report {ref} for {proj['name']} "
                         f"(DOB job {info['dob'].get('job_no') or 'TBD'}).")
        act("DOB/Forms", "Flagged for licensed review + manual signature. NOT auto-filed to DOB (human approval required).")
        task("DOB/Forms", f"Review & sign TR1 {ref}, then file with DOB", "Dana Whitfield, PE")
        result["artifacts"].append({"kind": "TR1 (draft — needs approval)", "ref": ref, "path": path})

    else:  # question
        from .config import SERVICES
        svc = SERVICES.get(info["sku"], {})
        rate_txt = (f"{money(svc.get('rate', 0))} per {svc.get('unit', 'visit')}"
                    if svc.get("rate_type") == "unit" else f"{money(svc.get('rate', 0))}/hr")
        draft = (f"Hi {cust.get('contact', '')},\n\nYes — we provide {svc.get('name', 'that service')}. "
                 f"Our rate is {rate_txt}. {svc.get('scope', '')}\n\nHappy to put together a quick proposal "
                 f"for your project whenever you're ready.\n\nBest,\n{COMPANY['short']} Team")
        act("Intake", f"Customer question from {cust['name']} — drafted a reply quoting {svc.get('name','the service')} at {rate_txt}.")
        task("Intake", f"Review & send reply to {cust['email']}", "Ops")
        result["reply_needed"] = True
        result["draft_reply"] = draft

    return result


# ---------------------------------------------------------------------------
# Follow-up agent — chase overdue invoices & expiring proposals
# ---------------------------------------------------------------------------
def run_followups(db, today=None):
    today = today or _dt.date.today()
    items = store.find_followups(db, today)
    out = []
    for it in items:
        if it["type"] == "overdue_invoice":
            draft = (f"Hi {it['customer']},\n\nA friendly reminder that invoice {it['ref']} for "
                     f"{money(it['amount'])} is now {it['days']} days past due. Could you let us know the "
                     f"expected payment date? Happy to resend the invoice.\n\nThank you,\n{COMPANY['short']} Accounting")
            store.log(db, "Follow-up", f"Invoice {it['ref']} is {it['days']} days overdue "
                                       f"({money(it['amount'])}) — drafted reminder to {it['customer']}.")
        else:
            draft = (f"Hi {it['customer']},\n\nJust a note that proposal {it['ref']} "
                     f"({money(it['amount'])}) expires in {it['days']} day(s). Let us know if you'd like to "
                     f"proceed or need any adjustments.\n\nBest,\n{COMPANY['short']} Team")
            store.log(db, "Follow-up", f"Proposal {it['ref']} expires in {it['days']} day(s) — "
                                       f"drafted nudge to {it['customer']}.")
        out.append({**it, "draft": draft})
    store.save(db)
    return out


def run_inbox(db, emails, today=None):
    results = [process_email(db, e, today=today) for e in emails]
    store.save(db)
    return results
