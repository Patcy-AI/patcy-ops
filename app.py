"""
app.py — Patcy Ops Console (Streamlit). The live demo: load the inbox, run the AI operations team,
and watch each specialist agent do real work and produce real documents.

Run:   streamlit run app.py
"""
import json
import os

import streamlit as st

from patcy import ops, store
from patcy.config import COMPANY, STAFF
from patcy.pricing import money

st.set_page_config(page_title="Patcy Ops — AI Operations Team", page_icon="🛠️", layout="wide")

AGENT_ICON = {"Intake": "📥", "Proposal": "📄", "Scheduling": "📅", "Payment": "💳",
              "DOB/Forms": "🏛️", "Follow-up": "🔔"}


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
    st.subheader("⚙️ What the team did")
    results = st.session_state.results

    tabs = st.tabs(["Activity feed", "Documents", "Schedule", "Follow-ups", "Tasks"])

    with tabs[0]:
        for r in results:
            st.markdown(f"**{r['subject']}**  ·  _{r['category'].replace('_', ' ')}_")
            for a in r["actions"]:
                st.markdown(f"&nbsp;&nbsp;{AGENT_ICON.get(a['agent'], '•')} **{a['agent']}** — {a['msg']}")
            if r.get("draft_reply"):
                with st.expander("✉️ Drafted reply"):
                    st.code(r["draft_reply"], language="text")
            st.markdown("---")

    with tabs[1]:
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

    with tabs[2]:
        sched = store.load()["schedule"]
        if not sched:
            st.info("Nothing scheduled.")
        for s in sched:
            st.markdown(f"📅 **{s['date']} {s['time']}** — {s['type']} inspection at *{s['project']}* → "
                        f"**{s['inspector']}**  ·  [Add to calendar]({s['link']})")

    with tabs[3]:
        fu = st.session_state.get("followups", [])
        if not fu:
            st.success("Nothing overdue.")
        for f in fu:
            label = ("💸 Overdue invoice" if f["type"] == "overdue_invoice" else "⏳ Expiring proposal")
            st.markdown(f"{label} **{f['ref']}** — {f['customer']} · {money(f['amount'])} · {f['days']} days")
            with st.expander("Drafted reminder"):
                st.code(f["draft"], language="text")

    with tabs[4]:
        tasks = store.load()["tasks"]
        if not tasks:
            st.info("No tasks.")
        for t in tasks:
            st.checkbox(f"{t['task']}  ·  _{t['owner'] or 'Unassigned'}_", key=t["ref"])

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
