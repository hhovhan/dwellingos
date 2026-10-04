import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.schema_validation import validate_rule

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "realpage-starter-pack" / "corpus" / "corpus_manifest.csv",
    ROOT / "realpage-starter-pack" / "data" / "sample_addresses.csv",
    ROOT / "output" / "rules.json", ROOT / "output" / "lookups.json",
    ROOT / "output" / "changes.json", ROOT / "output" / "quality_report.json",
    ROOT / "output" / "reference_case_report.json",
    ROOT / "output" / "audit_log.json", ROOT / "public" / "index.html",
    ROOT / "public" / "app.js", ROOT / "public" / "styles.css",
    ROOT / "docs" / "submission.md", ROOT / "docs" / "judge-guide.md",
    ROOT / "docs" / "assets" / "newark-passport.png",
    ROOT / "docs" / "architecture.md", ROOT / "docs" / "release-checklist.md",
    ROOT / "docs" / "method-note.md", ROOT / "docs" / "scale-architecture.md",
    ROOT / "docs" / "legal-review-packet.md",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.exists() or path.stat().st_size == 0]
if missing:
    raise SystemExit(f"Release check failed; missing: {', '.join(missing)}")

rules = json.loads((ROOT / "output" / "rules.json").read_text())["rules"]
schema = json.loads((ROOT / "realpage-starter-pack" / "schema" / "rule_record.schema.json").read_text())
schema_errors = [(rule.get("team_rule_id"), validate_rule(rule, schema)) for rule in rules]
schema_errors = [(rule_id, errors) for rule_id, errors in schema_errors if errors]
if schema_errors:
    raise SystemExit(f"Rule schema validation failed: {schema_errors[:5]}")
lookups = json.loads((ROOT / "output" / "lookups.json").read_text())["lookups"]
changes = json.loads((ROOT / "output" / "changes.json").read_text())
assert len(lookups) == 500
assert set(changes) == {"T1", "T2", "T3", "T4", "T5"}
assert rules and all(rule.get("source_url", "").startswith("https://") for rule in rules)
print(f"Release check passed: {len(rules)} rules, {len(lookups)} properties, 5 change scenarios, public judge documentation present")
