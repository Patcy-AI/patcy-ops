"""
documents.py — REAL PDF generation (proposals, invoices, TR1 forms) with ReportLab.

These are genuine, client-ready documents — not screenshots or mockups. Point Patcy at a real
customer and service and it produces a PDF you could actually send.
"""
import datetime as _dt
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from .config import COMPANY
from .pricing import money

BRAND = colors.HexColor("#1f3a5f")
LIGHT = colors.HexColor("#eef2f7")
GREY = colors.HexColor("#6b7280")

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_ss["Title"], textColor=BRAND, fontSize=20, spaceAfter=2)
H2 = ParagraphStyle("H2", parent=_ss["Heading2"], textColor=BRAND, fontSize=12, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=_ss["Normal"], fontSize=9.5, leading=14)
SMALL = ParagraphStyle("SMALL", parent=_ss["Normal"], fontSize=8, textColor=GREY, leading=11)
RIGHT = ParagraphStyle("RIGHT", parent=BODY, alignment=TA_RIGHT)


def _today():
    return _dt.date.today().strftime("%B %d, %Y")


def _header(story, doc_title, doc_ref):
    head = Table([[
        Paragraph(f"<b>{COMPANY['name']}</b><br/>{COMPANY['address']}<br/>{COMPANY['phone']} · {COMPANY['email']}"
                  f"<br/><font size=7 color='#6b7280'>{COMPANY['license']}</font>", BODY),
        Paragraph(f"<b><font size=15 color='#1f3a5f'>{doc_title}</font></b><br/>"
                  f"<font size=8 color='#6b7280'>{doc_ref}<br/>{_today()}</font>", RIGHT),
    ]], colWidths=[3.7 * inch, 3.0 * inch])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(head)
    story.append(Spacer(1, 6))
    story.append(Table([[""]], colWidths=[6.7 * inch],
                       style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 2, BRAND)])))
    story.append(Spacer(1, 10))


def _bill_to(story, customer, project):
    rows = [[Paragraph("<b>Client</b>", SMALL), Paragraph("<b>Project</b>", SMALL)],
            [Paragraph(f"{customer['name']}<br/>Attn: {customer.get('contact','')}<br/>"
                       f"{customer.get('address','')}<br/>{customer.get('email','')}", BODY),
             Paragraph(f"{project.get('name','—')}<br/>{project.get('address','')}<br/>"
                       f"Borough: {project.get('borough','—')}", BODY)]]
    t = Table(rows, colWidths=[3.35 * inch, 3.35 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, 0), 2)]))
    story.append(t)
    story.append(Spacer(1, 10))


def _items_table(story, quote):
    data = [["SKU", "Description", "Qty", "Unit", "Rate", "Amount"]]
    for it in quote["items"]:
        data.append([it["sku"], it["description"], f"{it['qty']:g}", it["unit"],
                     money(it["rate"]), money(it["amount"])])
    data.append(["", "", "", "", "Subtotal", money(quote["subtotal"])])
    if quote.get("discount"):
        data.append(["", "", "", "", f"Discount ({quote['discount_pct']:g}%)", "-" + money(quote["discount"])])
    data.append(["", "", "", "", "Total", money(quote["total"])])
    t = Table(data, colWidths=[0.75 * inch, 2.9 * inch, 0.5 * inch, 0.55 * inch, 0.9 * inch, 1.0 * inch])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -4), [colors.white, LIGHT]),
        ("LINEABOVE", (4, -1), (-1, -1), 1, BRAND), ("FONTNAME", (4, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style))
    story.append(t)


def generate_proposal(proposal: dict, out_dir="out") -> str:
    """proposal keys: ref, customer(dict), project(dict), quote(dict)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{proposal['ref']}.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    q = proposal["quote"]
    story = []
    _header(story, q["template"] or "Proposal", f"Proposal {proposal['ref']}")
    _bill_to(story, proposal["customer"], proposal["project"])
    story.append(Paragraph("Scope of Services", H2))
    story.append(Paragraph(q["scope"], BODY))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Fee Schedule", H2))
    _items_table(story, q)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Terms", H2))
    story.append(Paragraph(
        f"This proposal is valid for {COMPANY['proposal_valid_days']} days. Fees are billed monthly; "
        f"payment due Net {COMPANY['terms_days']}. Additional visits or overtime billed at the rates "
        f"above. Work performed per the applicable NYC Building Code and the firm's Special Inspection "
        f"Agency authorization.", BODY))
    story.append(Spacer(1, 22))
    sign = Table([[Paragraph("_____________________________<br/>Authorized — " + COMPANY["short"], BODY),
                   Paragraph("_____________________________<br/>Accepted — Client (sign & date)", BODY)]],
                 colWidths=[3.35 * inch, 3.35 * inch])
    story.append(sign)
    doc.build(story)
    return path


def generate_invoice(invoice: dict, out_dir="out") -> str:
    """invoice keys: ref, customer, project, quote, due_date, proposal_ref(optional)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{invoice['ref']}.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    q = invoice["quote"]
    story = []
    _header(story, "INVOICE", f"Invoice {invoice['ref']}")
    _bill_to(story, invoice["customer"], invoice["project"])
    meta = Paragraph(f"<b>Due date:</b> {invoice['due_date']} &nbsp;&nbsp; "
                     f"<b>Terms:</b> Net {COMPANY['terms_days']}" +
                     (f" &nbsp;&nbsp; <b>Ref proposal:</b> {invoice['proposal_ref']}"
                      if invoice.get("proposal_ref") else ""), SMALL)
    story.append(meta)
    story.append(Spacer(1, 8))
    _items_table(story, q)
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Amount due: {money(q['total'])}</b>", H2))
    story.append(Paragraph(f"Please remit to {COMPANY['name']} · {COMPANY['email']}. "
                           f"QuickBooks estimate/invoice sync available on connection.", SMALL))
    doc.build(story)
    return path


def generate_tr1(form: dict, out_dir="out") -> str:
    """A completed TR1-style Technical Report (Statement of Responsibility) PDF.
    form keys: ref, project(dict), customer(dict), inspections(list[str]), inspector(dict), dob(dict)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{form['ref']}.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    story = []
    _header(story, "TR1 — Technical Report", f"Statement of Responsibility · {form['ref']}")
    dob = form.get("dob", {})
    grid = [
        ["DOB Job / Filing No.", dob.get("job_no", "—"), "Block / Lot", dob.get("block_lot", "—")],
        ["Project Address", form["project"].get("address", "—"), "Borough", form["project"].get("borough", "—")],
        ["Owner / Client", form["customer"].get("name", "—"), "BIN", dob.get("bin", "—")],
        ["Special Inspection Agency", COMPANY["name"], "SIA No.", "SIA-01188"],
        ["Assigned Inspector", form.get("inspector", {}).get("name", "—"),
         "Engineer of Record", "Dana Whitfield, PE"],
    ]
    t = Table([[Paragraph(f"<b>{a}</b>", SMALL), Paragraph(str(b), BODY),
                Paragraph(f"<b>{c}</b>", SMALL), Paragraph(str(d), BODY)] for a, b, c, d in grid],
              colWidths=[1.55 * inch, 1.9 * inch, 1.2 * inch, 2.05 * inch])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d0dd")),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("BACKGROUND", (0, 0), (0, -1), LIGHT), ("BACKGROUND", (2, 0), (2, -1), LIGHT),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Required Special / Progress Inspections", H2))
    insp = form.get("inspections", [])
    rows = [["#", "Inspection", "Code Reference", "Status"]]
    for i, name in enumerate(insp, 1):
        rows.append([str(i), name, "NYC BC 1705", "Assigned"])
    it = Table(rows, colWidths=[0.4 * inch, 3.4 * inch, 1.6 * inch, 1.3 * inch])
    it.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BRAND), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7d0dd")),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(it)
    story.append(Spacer(1, 16))
    story.append(Paragraph("Statement of Responsibility", H2))
    story.append(Paragraph(
        "The undersigned Special Inspection Agency accepts responsibility for the special and progress "
        "inspections identified above, to be performed by qualified personnel in accordance with the "
        "approved construction documents and the NYC Building Code.", BODY))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "<b>DRAFT — prepared by Patcy Ops. Requires licensed review and manual signature/filing. "
        "Not submitted to DOB.</b>", SMALL))
    story.append(Spacer(1, 14))
    story.append(Table([[Paragraph("_____________________________<br/>Dana Whitfield, PE — EOR / Director of SI",
                                   BODY), Paragraph("Date: ____________", BODY)]],
                       colWidths=[4.2 * inch, 2.5 * inch]))
    doc.build(story)
    return path
