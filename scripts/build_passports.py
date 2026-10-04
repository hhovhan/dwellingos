import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "realpage-starter-pack" / "data" / "sample_addresses.csv"
OUTPUT = ROOT / "public" / "passports.json"

CATEGORIES = [
    "Rent increases",
    "Just-cause eviction",
    "Security deposits",
    "Application & screening fees",
    "Screening restrictions",
    "Algorithmic rent-setting",
]

LEGAL_CITY = {
    "Dorchester": "Boston",
    "Roxbury": "Boston",
    "East Boston": "Boston",
    "Brighton": "Boston",
    "Allston": "Boston",
    "South Boston": "Boston",
    "Jamaica Plain": "Boston",
    "Hyde Park": "Boston",
    "Mattapan": "Boston",
    "San Ysidro": "San Diego",
}


def missing(row, field, reason):
    if not (row.get(field) or "").strip():
        return {"field": field, "reason": reason, "severity": "blocking"}
    return None


with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
    rows = list(csv.DictReader(handle))

passports = []
for row in rows:
    legal_city = LEGAL_CITY.get(row["postal_city"], row["postal_city"])
    gaps = [
        missing(row, "zip", "Postal routing is incomplete; jurisdiction must be resolved from coordinates."),
        missing(row, "year_built", "Some rent rules depend on construction or occupancy date."),
        missing(row, "units", "Several exemptions and coverage tests depend on unit count."),
        {"field": "owner_type", "reason": "Owner identity was deliberately excluded from the challenge data.", "severity": "blocking"},
        {"field": "certificate_of_occupancy", "reason": "Year built cannot prove an occupancy-date cutoff.", "severity": "conditional"},
    ]
    gaps = [gap for gap in gaps if gap]
    passports.append({
        "id": row["address_id"],
        "address": row["street_address"],
        "postal_city": row["postal_city"],
        "legal_city": legal_city,
        "state": row["state"],
        "zip": row["zip"] or None,
        "year_built": int(row["year_built"]) if row["year_built"] else None,
        "units": int(float(row["units"])) if row["units"] else None,
        "use_code": row["use_code"],
        "use_description": row["use_description"],
        "source": row["source_dataset"],
        "retrieved_at": row["retrieved_at"],
        "missing": gaps,
        "rules": [{"category": category, "result": "awaiting_rule_engine"} for category in CATEGORIES],
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps({"generated_from": str(SOURCE), "count": len(passports), "passports": passports}, indent=2), encoding="utf-8")
print(f"Generated {len(passports)} auditable property passports at {OUTPUT}")
