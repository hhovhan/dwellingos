"""Score source-anchored, non-attorney reference decisions separately from pipeline tests."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import OUTPUT, ROOT, read_json, write_json
from engine.evaluator import evaluate

reference = read_json(ROOT / "quality" / "reference_cases.json")
rules = {rule["team_rule_id"]: rule for rule in read_json(OUTPUT / "rules.json")["rules"]}
results = []
for case in reference["cases"]:
    if case["rule_id"] not in rules:
        raise SystemExit(f"Reference case {case['id']} has no rule {case['rule_id']}")
    decision = evaluate(rules[case["rule_id"]], case["property"], case["as_of"])
    actual = decision["result"] if decision is not None else "excluded"
    results.append({"id": case["id"], "rule_id": case["rule_id"],
                    "expected": case["expected"], "actual": actual,
                    "passed": actual == case["expected"], "basis": case["basis"]})
report = {
    "review_status": reference["review_status"],
    "cases": len(results), "passed": sum(case["passed"] for case in results),
    "expected_distribution": dict(Counter(case["expected"] for case in results)),
    "results": results,
    "scope_note": "This is a small, hand-authored, source-anchored regression set. It is not an expert-reviewed legal gold set and does not measure corpus recall or production accuracy."
}
write_json(OUTPUT / "reference_case_report.json", report)
print(f"Reference cases: {report['passed']}/{report['cases']} matched; non-attorney regression set")
if report["passed"] != report["cases"]:
    raise SystemExit("Reference-case mismatch: " + ", ".join(case["id"] for case in results if not case["passed"]))
