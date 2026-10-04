import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Keep the organizer-provided starter pack inside this project so a clean
# checkout can reproduce every output without relying on a sibling directory.
PACK = ROOT / "realpage-starter-pack"
CORPUS = PACK / "corpus"
OUTPUT = ROOT / "output"
PUBLIC = ROOT / "public"
AS_OF = "2026-10-01"

CATEGORIES = {
    "rent_increase_limits": ("rent increase", "rent stabilization", "rent control", "rent-controlled", "annual adjustment", "annual allowable increase", "rental rate", "rent ceiling"),
    "just_cause_eviction": ("just cause", "terminate a tenancy", "termination of tenancy", "grounds for eviction", "notice to quit", "eviction"),
    "security_deposits": ("security deposit", "last month's rent", "deposit interest"),
    "application_screening_fees": ("screening fee", "application fee", "application screening"),
    "screening_restrictions": ("tenant screening", "criminal history", "fair chance", "source of income", "housing discrimination", "protected characteristic"),
    "algorithmic_rent_setting": ("algorithmic", "common pricing algorithm", "coordinated pricing algorithm", "rent pricing software"),
}

LEGAL_CITY_ALIASES = {
    "Dorchester": "Boston", "Roxbury": "Boston", "East Boston": "Boston",
    "Brighton": "Boston", "Allston": "Boston", "South Boston": "Boston",
    "Jamaica Plain": "Boston", "Hyde Park": "Boston", "Mattapan": "Boston",
    "San Ysidro": "San Diego", "Van Nuys": "Los Angeles",
}

VALID_RESULTS = {"applies", "unknown", "superseded", "not_yet_effective", "pending"}


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def source_body(text):
    lines = text.splitlines()
    return "\n".join(lines[3:]) if len(lines) > 3 and lines[0].startswith("SOURCE:") else text
