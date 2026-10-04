"""Score source-first holdouts without changing the locked annotations."""

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import normalize
from engine.law_intake import extract_candidates

ROOT = Path(__file__).resolve().parents[1]
cases = json.loads((ROOT / "quality/holdout_cases.json").read_text())
geocode = json.loads((ROOT / "output/geocode_evidence.json").read_text())["records"]
passports = {item["id"]: item for item in json.loads((ROOT / "public/passports.json").read_text())["passports"]}
raw = {item["address_id"]: item for item in csv.DictReader((ROOT / "realpage-starter-pack/data/sample_addresses.csv").open())}

extraction = []
for case in cases["extraction"]:
    source = (ROOT / f"realpage-starter-pack/corpus/text/{case['doc_id']}.txt").read_text()
    url = re.search(r"^SOURCE: (https://\S+)", source, re.M)
    if not url:
        raise ValueError(f"{case['id']}: source URL absent")
    candidates = extract_candidates(source, jurisdiction=case["jurisdiction"],
                                    source_url=url.group(1), retrieved_at="2026-10-01")
    if case.get("negative"):
        passed = not candidates
        finding = "clean negative" if passed else f"{len(candidates)} candidate(s) from status-only page"
    else:
        target = normalize(case["must_quote"]).casefold()
        if target not in normalize(source).casefold():
            raise ValueError(f"{case['id']}: locked quote is absent from original source")
        passed = any(candidate["category"] == case["category"] and target in candidate["quoted_span"].casefold()
                     for candidate in candidates)
        finding = "target found" if passed else "target missed or wrong category"
    extraction.append({"id": case["id"], "doc_id": case["doc_id"], "passed": passed,
                       "finding": finding, "candidate_count": len(candidates)})

address = []
for case in cases["addresses"]:
    address_id = case["id"]
    row, evidence, passport = raw[address_id], geocode[address_id], passports[address_id]
    checks = {"raw_record_preserved": passport["address"] == row["street_address"] and passport["state"] == row["state"],
              "geocoder_status": evidence["status"] == case["expected_geocode"] and passport["geocoder"]["status"] == evidence["status"],
              "city_boundary_not_proven": passport["city_boundary_needs_verification"] is True}
    if case.get("expected_city"):
        checks["matched_city"] = evidence.get("legal_city") == case["expected_city"] and passport["legal_city"] == case["expected_city"]
    if case.get("reason_contains"):
        checks["abstention_reason"] = case["reason_contains"] in evidence.get("reason", "")
    if "expected_zip_state_conflict" in case:
        checks["zip_state_conflict"] = passport["zip_state_conflict"] is case["expected_zip_state_conflict"]
    address.append({"id": address_id, "passed": all(checks.values()), "checks": checks})

report = {"annotation_method": cases["annotation_method"], "scope": cases["scope"],
          "extraction": {"passed": sum(x["passed"] for x in extraction), "total": len(extraction), "cases": extraction},
          "addresses": {"passed": sum(x["passed"] for x in address), "total": len(address), "cases": address},
          "limitations": ["Non-attorney source-first annotations; no independent legal expert review.",
                          "Targeted clauses do not measure corpus-wide recall or precision.",
                          "Census address-range matches are not parcel-boundary or legal-jurisdiction proof.",
                          "No access to the organizer's private scoring script or hidden cases."]}
target = ROOT / "output/holdout_report.json"
target.write_text(json.dumps(report, indent=2) + "\n")
print(f"Holdout extraction: {report['extraction']['passed']}/{report['extraction']['total']}; "
      f"address checks: {report['addresses']['passed']}/{report['addresses']['total']}")
for item in extraction + address:
    if not item["passed"]:
        print(f"FAIL {item['id']}: {item.get('finding', item.get('checks'))}")
if "--strict" in sys.argv and (report["extraction"]["passed"] != len(extraction) or report["addresses"]["passed"] != len(address)):
    raise SystemExit(1)
