"""
config.py — the firm's operating data that Patcy Ops runs on.

In production this comes from the client's CRM / QuickBooks / price book. Here it's a realistic,
editable profile for a NYC special-inspection & engineering firm, so every agent produces true,
firm-specific output (correct SKUs, correct pricing, real inspectors). Swap these values for a real
client's and the same code runs their business.
"""

COMPANY = {
    "name": "Meridian Structural Engineering, PLLC",
    "short": "Meridian",
    "address": "114 W 27th St, Suite 900, New York, NY 10001",
    "phone": "(212) 555-0170",
    "email": "ops@meridian-se.com",
    "license": "NY PE #099421 · Special Inspection Agency #SIA-01188",
    "terms_days": 30,
    "proposal_valid_days": 30,
}

# Service catalog with SKUs and rates. rate_type: 'hourly' | 'unit' | 'fixed'.
SERVICES = {
    "SI-CONC": {"name": "Concrete Testing & Special Inspection", "rate_type": "hourly", "rate": 165.0,
                "template": "Concrete Testing Proposal",
                "scope": "Field sampling, slump/air tests, cylinder casting & lab break tests, and "
                         "special inspection of cast-in-place concrete per NYC BC 1705.3."},
    "SI-STRUCT": {"name": "Structural Steel Special Inspection", "rate_type": "hourly", "rate": 175.0,
                  "template": "Special Inspection Proposal",
                  "scope": "Special inspection of structural steel, welding, and high-strength "
                           "bolting per NYC BC 1705.2."},
    "SO-OBS": {"name": "Structural Observation", "rate_type": "unit", "rate": 950.0, "unit": "visit",
               "template": "Structural Observation Proposal",
               "scope": "Periodic structural observation site visits by the Engineer of Record per "
                        "NYC BC 1704.6, with observation reports."},
    "FP-INSP": {"name": "Firestopping / Fireproofing Inspection", "rate_type": "hourly", "rate": 155.0,
                "template": "Special Inspection Proposal",
                "scope": "Special inspection of sprayed fire-resistant materials and penetration "
                         "firestopping per NYC BC 1705.14 / 1705.17."},
    "ENG-SVC": {"name": "Engineering Services (TR1/TR8 filing & design support)", "rate_type": "hourly",
                "rate": 210.0, "template": "Engineering Services Proposal",
                "scope": "Preparation of DOB TR1/TR8 technical reports, filing support, and "
                         "engineering review."},
    "MOB": {"name": "Mobilization / Trip Charge", "rate_type": "unit", "rate": 85.0, "unit": "trip",
            "template": None, "scope": "Per-visit mobilization to the project site."},
}

# Inspector / staff roster with certifications and boroughs they cover.
STAFF = [
    {"id": "insp_01", "name": "Andre Silva",   "role": "Special Inspector",
     "certs": ["Concrete", "Firestopping"], "boroughs": ["Manhattan", "Brooklyn"], "email": "andre@meridian-se.com"},
    {"id": "insp_02", "name": "Priya Nadkarni", "role": "Special Inspector",
     "certs": ["Structural Steel", "Welding"], "boroughs": ["Manhattan", "Queens"], "email": "priya@meridian-se.com"},
    {"id": "insp_03", "name": "Marcus Bell",    "role": "Field Technician",
     "certs": ["Concrete"], "boroughs": ["Bronx", "Manhattan"], "email": "marcus@meridian-se.com"},
    {"id": "eng_01",  "name": "Dana Whitfield, PE", "role": "Engineer of Record",
     "certs": ["Structural Observation", "TR1", "TR8"], "boroughs": ["All"], "email": "dana@meridian-se.com"},
]

# A few known customers (in production this is the CRM / QuickBooks customer list).
CUSTOMERS = {
    "acme": {"name": "Acme Development LLC", "contact": "Jordan Pierce", "email": "jpierce@acmedev.com",
             "address": "500 5th Ave, New York, NY 10110"},
    "hudson": {"name": "Hudson Yards Builders", "contact": "Lena Ortiz", "email": "lena@hudsonyb.com",
               "address": "20 Hudson Yards, New York, NY 10001"},
    "brightline": {"name": "Brightline Contracting", "contact": "Sam Whitaker", "email": "sam@brightlinegc.com",
                   "address": "88 Jay St, Brooklyn, NY 11201"},
}


def find_service(text: str):
    """Best-effort map free text to a service SKU (the LLM also does this; this is the deterministic
    fallback / validator)."""
    t = (text or "").lower()
    if "concrete" in t:
        return "SI-CONC"
    if "steel" in t or "weld" in t or "bolt" in t:
        return "SI-STRUCT"
    if "observation" in t:
        return "SO-OBS"
    if "fire" in t:
        return "FP-INSP"
    if any(k in t for k in ["tr1", "tr8", "filing", "engineering", "design"]):
        return "ENG-SVC"
    return "SI-STRUCT"
