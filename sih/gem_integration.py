import json
import time

# Realistic GeM (Government e-Marketplace) Active Tenders Dataset
GEM_TENDERS_DATA = [
    {
        "gem_bid_id": "GEM/2026/B/5891023",
        "ministry": "Ministry of Power & Energy",
        "dept": "Central Public Works Department (CPWD)",
        "item_name": "LED Street Lighting Systems & Luminaires",
        "quantity": "5,000 Units",
        "closing_date": "2026-09-25",
        "tender_value_inr": "₹ 1,25,000,000",
        "specifications": "Procurement of self-ballasted LED street light luminaires rated 60W, working voltage 240V AC 50Hz, IP65 ingress protection, surge protection 10kV, luminous efficacy > 110 lm/W, CRI >= 80, and thermal dissipation management.",
        "category": "Electrical & Lighting"
    },
    {
        "gem_bid_id": "GEM/2026/B/4910245",
        "ministry": "Ministry of Railways",
        "dept": "Indian Railways Central Armoured Supply",
        "item_name": "Heavy Duty PVC Insulated Copper Power Cables 1100V",
        "quantity": "12,000 Meters",
        "closing_date": "2026-09-30",
        "tender_value_inr": "₹ 8,400,000",
        "specifications": "Supply of multicore polyvinyl chloride PVC insulated sheathed heavy duty flexible cables for 1100V working voltage. Must feature high purity copper conductors, flame retardant low smoke (FRLS) insulation, and high dielectric strength.",
        "category": "Electrical & Cables"
    },
    {
        "gem_bid_id": "GEM/2026/B/6120938",
        "ministry": "Ministry of New and Renewable Energy (MNRE)",
        "dept": "Solar Energy Corporation of India (SECI)",
        "item_name": "Crystalline Photovoltaic (PV) Solar Modules",
        "quantity": "10,000 Modules",
        "closing_date": "2026-10-05",
        "tender_value_inr": "₹ 45,000,000",
        "specifications": "High efficiency crystalline silicon terrestrial PV modules rated 400W for solar park installations. Must comply with damp heat test, thermal cycling -40C to +85C, mechanical load 5400Pa, and hail impact type approval.",
        "category": "Renewable Energy & Solar"
    },
    {
        "gem_bid_id": "GEM/2026/B/7281094",
        "ministry": "State Electricity Distribution Board",
        "dept": "Urban Infrastructure & Substation Cell",
        "item_name": "Outdoor Oil Immersed Distribution Transformers 33kV",
        "quantity": "150 Units",
        "closing_date": "2026-10-12",
        "tender_value_inr": "₹ 62,500,000",
        "specifications": "Outdoor type oil immersed distribution transformers up to 2500 kVA rating, 33kV primary voltage. Requires strict energy efficiency class loss limits at 50% and 100% load, short circuit withstand test, and ONAN cooling.",
        "category": "Power Distribution"
    },
    {
        "gem_bid_id": "GEM/2026/B/8390112",
        "ministry": "Ministry of Housing and Urban Affairs",
        "dept": "Smart Cities Mission Project",
        "item_name": "Smart AC Static Watt-Hour Energy Meters Class 1",
        "quantity": "25,000 Units",
        "closing_date": "2026-10-18",
        "tender_value_inr": "₹ 37,500,000",
        "specifications": "AC static watt-hour electricity meters class 1 accuracy for active energy measurement in commercial smart grids. Must include electromagnetic compatibility EMC shielding, tamper detection, and optical communication interface.",
        "category": "Metering & Smart Grid"
    }
]

def get_gem_tenders():
    """Returns the list of active GeM procurement tenders."""
    return GEM_TENDERS_DATA

def get_gem_tender_by_id(gem_bid_id):
    """Finds a specific GeM tender by its Bid ID."""
    for tender in GEM_TENDERS_DATA:
        if tender['gem_bid_id'].lower() == gem_bid_id.lower():
            return tender
    return None

def generate_gem_procurement_clause(standard_number, standard_title, category="Electrical"):
    """
    Generates a GeM-compliant procurement clause text suitable for insertion into
    official GeM Tender documents & Technical Evaluation Reports.
    """
    clause_text = (
        f"GeM MANDATORY BIS COMPLIANCE CLAUSE:\n"
        f"The offered item/equipment under this GeM tender MUST strictly conform to the Bureau of Indian Standards "
        f"specification: {standard_number} - '{standard_title}'. Vendor must submit valid BIS Registration / License "
        f"certificate issued by BIS along with the technical bid on the GeM Portal as per GeM GTC Clause 4.1.2."
    )
    return clause_text

def get_gem_search_url(query):
    """Constructs direct search URL to Government e-Marketplace (GeM) Marketplace."""
    encoded_query = urllib_quote(query)
    return f"https://mkp.gem.gov.in/search?q={encoded_query}"

def urllib_quote(text):
    """Simple URL encoder helper for GeM search links."""
    import urllib.parse
    return urllib.parse.quote(text)

if __name__ == "__main__":
    print(f"GeM Integration Module loaded with {len(GEM_TENDERS_DATA)} sample procurement tenders.")
