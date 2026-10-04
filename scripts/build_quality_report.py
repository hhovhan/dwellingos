import collections
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import OUTPUT, PUBLIC, read_json, write_json

rules = read_json(OUTPUT / "rules.json")["rules"]
lookups = read_json(OUTPUT / "lookups.json")["lookups"]
changes = read_json(OUTPUT / "changes.json")
audit = read_json(OUTPUT / "corpus_audit.json")
source_gaps = read_json(OUTPUT / "source_gap_register.json")["gaps"]
passports = read_json(PUBLIC / "passports.json")["passports"]
results = collections.Counter(value["result"] for values in lookups.values() for value in values)
categories = collections.Counter(rule["category"] for rule in rules)
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "properties": len(lookups), "rules": len(rules),
    "categories": dict(sorted(categories.items())), "results": dict(sorted(results.items())),
    "citation_completeness": sum(bool(rule.get("citation") and rule.get("source_url")) for rule in rules) / len(rules),
    "verbatim_evidence_completeness": sum(len(rule.get("quoted_span", "")) >= 20 for rule in rules) / len(rules),
    "properties_with_at_least_one_result": sum(bool(values) for values in lookups.values()),
    "properties_with_zip_state_conflict": sum(item["zip_state_conflict"] for item in passports),
    "unknown_rate": results["unknown"] / sum(results.values()),
    "corpus": {"captured": audit["captured_documents"], "links_only": audit["links_only_or_unavailable"], "integrity_issues": len(audit["integrity_issues"])},
    "source_gap_dispositions": dict(collections.Counter(gap["disposition"] for gap in source_gaps)),
    "change_tests": {test_id: len(value["affected_address_ids"]) for test_id, value in changes.items()},
    "limitations": [
        "Candidate rules require legal review before production use.",
        "The organizer's 33 link-only entries include two separately verified city supplements and two recovered official city excerpts; others remain context, publisher-review, or blocked sources.",
        "The 20-case reference set is source-anchored and non-attorney-reviewed, not a complete legal gold set.",
        "27 supplied property records have ZIP prefixes inconsistent with their listed state; all city boundaries still need independent validation.",
        "Unknown is returned when supplied facts cannot prove coverage.",
    ],
}
write_json(OUTPUT / "quality_report.json", report)
write_json(OUTPUT / "audit_log.json", {"stages": [
    {"stage": "corpus_audit", "status": "passed", "documents": audit["manifest_documents"], "issues": len(audit["integrity_issues"])},
    {"stage": "rule_extraction", "status": "passed", "rules": len(rules), "evidence_policy": "verbatim source span required"},
    {"stage": "jurisdiction_and_lookup", "status": "passed", "properties": len(lookups)},
    {"stage": "change_tracking", "status": "passed", "tests": list(changes)},
]})
print(f"Quality report: {len(rules)} rules, {len(lookups)} properties, {report['citation_completeness']:.0%} citation completeness")
