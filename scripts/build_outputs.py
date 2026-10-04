import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import AS_OF, OUTPUT, PACK, PUBLIC, read_csv, read_json, write_json
from engine.evaluator import evaluate, resolve_jurisdiction
from engine.change_tracker import build_changes

addresses = read_csv(PACK / "data" / "sample_addresses.csv")
rules = read_json(OUTPUT / "rules.json")["rules"]
geocodes = read_json(OUTPUT / "geocode_evidence.json")["records"] if (OUTPUT / "geocode_evidence.json").exists() else {}
lookups = {}
passports = []
CATEGORY_ORDER = ["rent_increase_limits", "just_cause_eviction", "security_deposits", "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting"]
RESULT_PRIORITY = {"applies": 5, "superseded": 4, "unknown": 3, "not_yet_effective": 2, "pending": 1}
SCENARIO_FIELDS = {
    "D010": ("DND_or_BPDA_program_participation", ("yes", "no")),
    "NEWARK-RENT-01": ("rent_control_status", ("covered", "exempt")),
    "SD-INCOME-01": ("owner_occupied_shared_kitchen_or_bath", ("yes", "no")),
    "D024": ("rent_control_status", ("covered", "exempt")),
    "D080": ("rent_control_status", ("covered", "exempt")),
}
STATE_ZIP_PREFIXES = {"CA": ("9",), "MA": ("01", "02"), "NJ": ("07", "08")}


def decision_snapshot(rule, row, as_of):
    decision = evaluate(rule, row, as_of)
    return ({"result": decision["result"], "explanation": decision["explanation"],
             "missing_coverage_facts": decision["missing_coverage_facts"]}
            if decision else {"result": "excluded", "explanation": "This rule is not in the applied-rule set for these facts and date.",
                              "missing_coverage_facts": []})


def decision_table(rule, row):
    """Materialize browser scenarios through the same Python evaluator as exports."""
    def dates(facts):
        return {"before": decision_snapshot(rule, facts, "0001-01-01"),
                "active": decision_snapshot(rule, facts, rule.get("valid_through") or "2026-10-01"),
                "after": decision_snapshot(rule, facts, "9999-12-31")}

    table = {"default": dates(row)}
    if rule["source_doc_id"] == "D024":
        table["scenario_window"] = {"start": "2026-03-01", "end": "2027-02-28"}
    scenario = SCENARIO_FIELDS.get(rule["team_rule_id"], SCENARIO_FIELDS.get(rule["source_doc_id"]))
    if scenario:
        field, values = scenario
        table["scenario_field"] = field
        table["choices"] = {value: dates({**row, field: value}) for value in values}
    return table

for row in addresses:
    jurisdiction = resolve_jurisdiction(row)
    geocode = geocodes.get(row["address_id"], {"status": "not_checked"})
    zip_state_conflict = bool(row["zip"] and not row["zip"].startswith(STATE_ZIP_PREFIXES[row["state"]]))
    evaluations = [value for rule in rules if (value := evaluate(rule, row, AS_OF))]
    lookups[row["address_id"]] = evaluations
    gaps = []
    for field, reason in (
        ("zip", "Postal routing is incomplete; jurisdiction requires independent validation."),
        ("year_built", "Some rule coverage depends on construction or occupancy date."),
        ("units", "Several exemptions and coverage tests depend on unit count."),
    ):
        if not row.get(field, "").strip():
            gaps.append({"field": field, "reason": reason, "severity": "blocking"})
    gaps.extend([
        {"field": "owner_type", "reason": "Owner identity was deliberately excluded from the challenge data.", "severity": "blocking"},
        {"field": "certificate_of_occupancy", "reason": "Year built cannot prove an occupancy-date cutoff.", "severity": "conditional"},
    ])
    if zip_state_conflict:
        gaps.append({"field": "zip_state_conflict", "reason": "The supplied ZIP prefix conflicts with the supplied state. Address and legal jurisdiction require independent verification.", "severity": "blocking"})
    rule_by_id = {rule["team_rule_id"]: rule for rule in rules}
    decorated = [{**result, "category": rule_by_id[result["team_rule_id"]]["category"],
                  "title": rule_by_id[result["team_rule_id"]]["title"],
                  "requirement": rule_by_id[result["team_rule_id"]]["requirement"],
                  "quoted_span": rule_by_id[result["team_rule_id"]]["quoted_span"],
                  "coverage_conditions": rule_by_id[result["team_rule_id"]]["coverage_conditions"],
                  "exemptions": rule_by_id[result["team_rule_id"]]["exemptions"],
                  "effective_date": rule_by_id[result["team_rule_id"]]["effective_date"],
                  "valid_through": rule_by_id[result["team_rule_id"]].get("valid_through"),
                  "source_doc_id": rule_by_id[result["team_rule_id"]]["source_doc_id"],
                  "retrieved_at": rule_by_id[result["team_rule_id"]].get("retrieved_at"),
                  "rule_status": rule_by_id[result["team_rule_id"]]["status"],
                  "key_value": rule_by_id[result["team_rule_id"]].get("key_value"),
                  "citation": rule_by_id[result["team_rule_id"]]["citation"],
                  "source_url": rule_by_id[result["team_rule_id"]]["source_url"],
                  "decision_table": decision_table(rule_by_id[result["team_rule_id"]], row)} for result in evaluations]
    grouped = []
    for category in CATEGORY_ORDER:
        matches = [value for value in decorated if value["category"] == category]
        grouped.append({"category": category,
                        "result": max(matches, key=lambda value: RESULT_PRIORITY[value["result"]])["result"] if matches else "unknown",
                        "rules": matches,
                        "evidence_count": len(matches)})
    passports.append({
        "id": row["address_id"], "address": row["street_address"],
        "postal_city": row["postal_city"], "legal_city": jurisdiction["legal_city"],
        "jurisdiction_method": jurisdiction["method"], "state": row["state"],
        "geocoder": geocode,
        "city_boundary_needs_verification": jurisdiction["method"] == "dataset_postal_city_assumed",
        "zip_state_conflict": zip_state_conflict,
        "zip": row["zip"] or None,
        "year_built": int(row["year_built"]) if row["year_built"] else None,
        "units": int(float(row["units"])) if row["units"] else None,
        "use_code": row["use_code"], "use_description": row["use_description"],
        "source": row["source_dataset"], "retrieved_at": row["retrieved_at"],
        "missing": gaps,
        "rules": decorated, "categories": grouped,
    })

changes = build_changes(addresses, rules)
source_gaps = read_json(OUTPUT / "source_gap_register.json")["gaps"]
write_json(OUTPUT / "lookups.json", {"as_of": AS_OF, "lookups": lookups})
write_json(OUTPUT / "changes.json", changes)
write_json(PUBLIC / "system.json", {
    "as_of": AS_OF, "properties": len(passports), "rules": len(rules),
    "captured_sources": 54, "link_only_sources": 33,
    "zip_state_conflicts": sum(passport["zip_state_conflict"] for passport in passports),
    "geocode_counts": {status: sum(passport["geocoder"]["status"] == status for passport in passports)
                       for status in ("matched", "unresolved", "conflict", "not_checked")},
    "evaluations": sum(map(len, lookups.values())),
    "change_tests": {key: {"affected": len(value["affected_address_ids"]), "conflicts": len(value["conflict_flag_address_ids"]), "affected_address_ids": value["affected_address_ids"], "notes": value["notes"]} for key, value in changes.items()},
    "source_gaps": {
        "context_only": sum(gap["disposition"] == "context_only_official_source_preferred" for gap in source_gaps),
        "terms_review": sum(gap["disposition"] == "terms_review_required_not_captured" for gap in source_gaps),
        "capture_blocked": sum(gap["disposition"] == "official_source_capture_blocked" for gap in source_gaps),
        "supplemented": sum(gap["disposition"] == "covered_by_verified_supplement" for gap in source_gaps),
        "recovered_official": sum(gap["disposition"] == "recovered_from_official_city_source" for gap in source_gaps),
    },
})
write_json(PUBLIC / "passports.json", {"generated_from": "official RealPage starter pack", "as_of": AS_OF, "count": len(passports), "passports": passports})
print(f"Built {len(passports)} passports and {sum(map(len, lookups.values()))} evidence-linked evaluations")
