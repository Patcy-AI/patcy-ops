"""
app.py — Patcy Ops Console (Streamlit). The live demo: load the inbox, run the AI operations team,
and watch each specialist agent do real work and produce real documents.

Run:   streamlit run app.py
"""
import json
import os

import streamlit as st

try:                                  # load GROQ_API_KEY (and other secrets) from a local .env if present
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from patcy import ops, store
from patcy.config import COMPANY, STAFF
from patcy.pricing import money

st.set_page_config(page_title="Patcy Ops — AI Operations Team", page_icon="🛠️", layout="wide")

AGENT_ICON = {"Intake": "📥", "Proposal": "📄", "Scheduling": "📅", "Payment": "💳",
              "DOB/Forms": "🏛️", "Follow-up": "🔔", "Security": "🛡️", "Guardrail": "🔒"}


def load_inbox():
    with open(os.path.join(os.path.dirname(__file__), "data", "inbox.json")) as f:
        return json.load(f)


# ---- header ----
left, right = st.columns([3, 1])
with left:
    st.title("🛠️ Patcy Ops")
    st.caption(f"An AI operations team for **{COMPANY['name']}** — reads the inbox, "
               f"writes proposals, schedules inspectors, invoices, files forms, and follows up.")
with right:
    st.metric("Specialist agents", "7")
    st.caption("Intake · Proposal · Scheduling · Invoicing · Payment · DOB/Forms · Follow-up")

st.divider()

# ---- session ----
if "ran" not in st.session_state:
    st.session_state.ran = False

col_a, col_b, col_c = st.columns([1, 1, 4])
with col_a:
    run = st.button("▶ Run Patcy Ops", type="primary", use_container_width=True)
with col_b:
    if st.button("↺ Reset", use_container_width=True):
        st.session_state.ran = False
        st.rerun()

inbox = load_inbox()

# ---- inbox preview ----
st.subheader("📨 Incoming inbox")
for e in inbox:
    with st.expander(f"**{e['subject']}**  —  {e['from']}"):
        st.write(e["body"])

if run:
    db = store.seed_demo()
    st.session_state.results = ops.run_inbox(db, inbox)
    st.session_state.followups = ops.run_followups(store.load())
    st.session_state.ran = True

# ---- results ----
if st.session_state.get("ran"):
    st.divider()
    results = st.session_state.results
    db_now = store.load()
    approvals = db_now.get("approvals", [])
    pending = [a for a in approvals if a["status"] == "pending"]
    flagged = [r for r in results if r.get("security", {}).get("flagged")]

    # Guardrail headline — security is a first-class part of the demo.
    m1, m2, m3 = st.columns(3)
    m1.metric("Actions prepared", sum(len(r["actions"]) for r in results))
    m2.metric("🔒 Held for approval", len(pending))
    m3.metric("🛡️ Injection blocked", len(flagged))

    st.subheader("⚙️ What the team did")
    tabs = st.tabs(["🔒 Needs approval", "🛡️ Security", "Activity feed",
                    "Documents", "Schedule", "Follow-ups", "Tasks"])

    # --- Needs approval (human-in-the-loop) ---
    with tabs[0]:
        st.caption("High-risk actions — money movement, DOB filings, high-value sends — are **held** "
                   "here. Nothing irreversible runs without a human. _OWASP LLM06 Excessive Agency · "
                   "NIST AI RMF human oversight · EU AI Act._")
        if not approvals:
            st.info("No high-risk actions in this batch.")
        for a in approvals:
            icon = {"pending": "⏳", "approved": "✅", "rejected": "🚫"}.get(a["status"], "•")
            with st.container(border=True):
                amt = f"  ·  {money(a['amount'])}" if a.get("amount") else ""
                st.markdown(f"{icon} **{a['title']}**{amt}  —  _{a['status']}_")
                if a.get("flagged"):
                    st.warning("⚠ Originated from an email flagged for prompt injection — review carefully. "
                               + a.get("flag_note", ""))
                st.caption(f"**Why it's gated:** {a['reason']}")
                st.caption(f"**Control:** {a['control']}")
                st.caption(f"**Frameworks:** {a['frameworks']}")
                if a["status"] == "pending":
                    c1, c2, _ = st.columns([1, 1, 4])
                    if c1.button("✅ Approve", key=f"ap{a['ref']}", use_container_width=True):
                        ops.apply_approval(store.load(), a["ref"], "approve")
                        st.rerun()
                    if c2.button("🚫 Reject", key=f"rj{a['ref']}", use_container_width=True):
                        ops.apply_approval(store.load(), a["ref"], "reject")
                        st.rerun()

    # --- Security (untrusted-inbox defense) ---
    with tabs[1]:
        st.caption("The inbox is **untrusted input**. Every message is scanned for prompt injection / "
                   "authority-escalation before any action runs. _OWASP LLM01 Prompt Injection · LLM04._")
        for r in results:
            s = r.get("security", {})
            if s.get("flagged"):
                st.error(f"🚫 **{r['subject']}** — injection detected. {s['note']}")
                st.caption("Matched signatures: `" + "`, `".join(s.get("hits", [])[:5]) + "`")
            else:
                st.markdown(f"✅ {r['subject']} — clean")

    # --- Activity feed ---
    with tabs[2]:
        for r in results:
            st.markdown(f"**{r['subject']}**  ·  _{r['category'].replace('_', ' ')}_")
            for a in r["actions"]:
                st.markdown(f"&nbsp;&nbsp;{AGENT_ICON.get(a['agent'], '•')} **{a['agent']}** — {a['msg']}")
            if r.get("draft_reply"):
                with st.expander("✉️ Drafted reply"):
                    st.code(r["draft_reply"], language="text")
            st.markdown("---")

    with tabs[3]:
        docs = [a for r in results for a in r["artifacts"] if a.get("path")]
        if not docs:
            st.info("No documents generated.")
        cols = st.columns(2)
        for i, d in enumerate(docs):
            with cols[i % 2]:
                st.markdown(f"**{d['kind']} — {d['ref']}**"
                            + (f"  ·  {money(d['amount'])}" if d.get("amount") else ""))
                try:
                    with open(d["path"], "rb") as fh:
                        st.download_button("⬇ Download PDF", fh.read(), file_name=os.path.basename(d["path"]),
                                           mime="application/pdf", key=f"dl{i}", use_container_width=True)
                except FileNotFoundError:
                    st.caption("(file not found)")

    with tabs[4]:
        sched = store.load()["schedule"]
        if not sched:
            st.info("Nothing scheduled.")
        for s in sched:
            st.markdown(f"📅 **{s['date']} {s['time']}** — {s['type']} inspection at *{s['project']}* → "
                        f"**{s['inspector']}**  ·  [Add to calendar]({s['link']})")

    with tabs[5]:
        fu = st.session_state.get("followups", [])
        if not fu:
            st.success("Nothing overdue.")
        for f in fu:
            label = ("💸 Overdue invoice" if f["type"] == "overdue_invoice" else "⏳ Expiring proposal")
            st.markdown(f"{label} **{f['ref']}** — {f['customer']} · {money(f['amount'])} · {f['days']} days")
            with st.expander("Drafted reminder"):
                st.code(f["draft"], language="text")

    with tabs[6]:
        tasks = store.load()["tasks"]
        if not tasks:
            st.info("No tasks.")
        for t in tasks:
            st.checkbox(f"{t['task']}  ·  _{t['owner'] or 'Unassigned'}_", key=t["ref"])

# ---- Ask Patcy: the conversational layer (Groq) ----
st.divider()
st.subheader("💬 Ask Patcy")
from patcy import assistant, llm  # noqa: E402
if llm.available():
    st.caption("Ask about your operations, priorities, or ask Patcy to draft something. "
               "Patcy reasons and drafts — it never sends or moves money without your approval.")
else:
    st.caption("⚠ No `GROQ_API_KEY` set yet — Patcy will answer from the current state, but add the "
               "key (Settings/secrets) to turn on full conversation.")

if "chat" not in st.session_state:
    st.session_state.chat = []
for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(msg)
_prompt = st.chat_input("Ask Patcy… e.g. “what needs my approval and why?”")
if _prompt:
    st.session_state.chat.append(("user", _prompt))
    with st.chat_message("user"):
        st.markdown(_prompt)
    with st.chat_message("assistant"):
        with st.spinner("Patcy is thinking…"):
            _ans = assistant.reply(st.session_state.chat, store.load())
        st.markdown(_ans)
    st.session_state.chat.append(("assistant", _ans))

# ---- sidebar: the team + the honest scope ----
with st.sidebar:
    st.subheader("The team")
    for s in STAFF:
        st.markdown(f"**{s['name']}** — {s['role']}  \n_{', '.join(s['certs'])} · {', '.join(s['boroughs'])}_")
    st.divider()
    st.subheader("What's real vs. integrated")
    st.markdown(
        "**Real now:** proposal PDFs w/ live pricing, invoices, TR1 forms, scheduling + inspector "
        "assignment, classification, follow-up drafts.\n\n"
        "**Integration points** (need the client's login + approval): QuickBooks sync, sending from "
        "their Gmail, DOB filing. Wired as documented connectors — never auto-submitted."
    )
