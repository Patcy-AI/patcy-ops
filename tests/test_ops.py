"""
Tests for the Patcy Ops pipeline — proves each agent produces the right real output. No LLM needed.
Run:  python tests/test_ops.py
"""
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, ".."))
os.environ["PATCY_DB"] = os.path.join(tempfile.gettempdir(), "patcy_test_db.json")

from patcy import ops, store  # noqa: E402
from patcy.pricing import build_quote  # noqa: E402


def _inbox():
    with open(os.path.join(_HERE, "..", "data", "inbox.json")) as f:
        return json.load(f)


def test_pricing_math():
    q = build_quote("SI-CONC", 40, add_mobilization=6, discount_pct=5)
    assert q["items"][0]["amount"] == 6600.0 and q["total"] == 6754.5


def test_classify_categories():
    got = {e["id"]: ops.classify(e)["category"] for e in _inbox()}
    assert got["e1"] == "proposal_request"
    assert got["e2"] == "inspection_request"
    assert got["e3"] == "payment"
    assert got["e4"] == "tr1_request"
    assert got["e5"] == "question"


def test_full_pipeline_produces_artifacts():
    db = store.seed_demo()
    results = ops.run_inbox(db, _inbox())
    kinds = [a["kind"] for r in results for a in r["artifacts"]]
    assert any("Proposal" in k for k in kinds)
    assert any("TR1" in k for k in kinds)
    assert any(r["category"] == "inspection_request" for r in results)


def test_payment_marks_invoice_paid():
    db = store.seed_demo()
    ops.run_inbox(db, _inbox())
    db = store.load()
    inv = next(i for i in db["invoices"] if i["ref"] == "INV-2026-0298")
    assert inv["status"] == "paid"


def test_inspector_assignment_matches_cert():
    insp = ops.assign_inspector("SI-STRUCT", "Manhattan")
    assert "Structural Steel" in insp["certs"]


def test_followups_finds_overdue_and_expiring():
    db = store.seed_demo()
    ops.run_inbox(db, _inbox())
    fu = ops.run_followups(store.load())
    types = {f["type"] for f in fu}
    assert "overdue_invoice" in types and "expiring_proposal" in types


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn(); passed += 1; print("PASS", fn.__name__)
    print(f"\n{passed}/{len(fns)} tests passed")
