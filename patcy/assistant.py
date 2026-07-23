"""
assistant.py — the conversational layer. Talk to Patcy in plain language; it answers with the Groq
LLM, grounded in the live operations state (pending approvals, tasks, invoices). It can explain,
summarize, prioritize, and draft — but per the guardrails it NEVER moves money, files, or sends on
its own. It drafts and recommends; a human approves.

Fail-safe: with no GROQ_API_KEY it still answers from the context via a template, so the app runs.
"""
from . import llm, store

SYSTEM = (
    "You are Patcy, an AI operations assistant for a small business. You are warm, concise, and "
    "practical. You help the user understand what's happening in their operations, what needs their "
    "attention, and you draft messages and next steps.\n"
    "HARD RULES: You never move money, file documents with any agency, or send any email/message on "
    "your own. You draft and recommend; a human approves. If asked to do something high-risk, say it "
    "will be queued for their approval. Ground every answer in the CONTEXT provided; if you don't "
    "know something, say so plainly rather than inventing it."
)


def _context(db):
    """A compact snapshot of the live state, so the model answers from reality, not guesses."""
    pending = [a for a in db.get("approvals", []) if a.get("status") == "pending"]
    tasks = db.get("tasks", [])
    invoices = db.get("invoices", [])
    parts = []
    parts.append("PENDING APPROVALS (" + str(len(pending)) + "): " +
                 ("; ".join(f"{a['title']} — {a['reason']}" for a in pending[:8]) or "none"))
    parts.append("OPEN TASKS (" + str(len(tasks)) + "): " +
                 ("; ".join(f"{t['task']} (owner: {t.get('owner') or '—'})" for t in tasks[:8]) or "none"))
    parts.append("INVOICES: " +
                 ("; ".join(f"{i['ref']} {i.get('status')} ${i.get('amount')}" for i in invoices[:8]) or "none"))
    return "\n".join(parts)


def reply(history, db=None):
    """Generate Patcy's next turn. `history` is a list of (role, message); the last entry is the
    user's latest message. Returns the assistant's reply text."""
    db = db if db is not None else store.load()
    ctx = _context(db)
    convo = ""
    for role, msg in history[-8:]:
        convo += f"{role.upper()}: {msg}\n"
    user = ("CONTEXT (current operations state):\n" + ctx +
            "\n\nCONVERSATION:\n" + convo + "PATCY:")
    fallback = ("I can see " + ctx.split(chr(10))[0].lower() +
                ". Add a GROQ_API_KEY to turn on full conversation, and I'll be able to reason, "
                "summarize, and draft in plain language.")
    return llm.chat(SYSTEM, user, fallback=fallback, temperature=0.4, max_tokens=500)
