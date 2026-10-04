"""Record a human-reviewed law candidate for the next pipeline run."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import ROOT, read_json, write_json
from engine.law_intake import approve_candidate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("proposals", type=Path)
parser.add_argument("candidate_id")
parser.add_argument("--title", required=True)
parser.add_argument("--citation", required=True)
parser.add_argument("--status", choices=["in_force", "not_yet_effective", "pending", "failed"], required=True)
parser.add_argument("--coverage-conditions", required=True)
parser.add_argument("--effective-date")
parser.add_argument("--exemptions")
parser.add_argument("--penalty")
parser.add_argument("--coverage-json", help="Reviewed conditions, e.g. '[{\"field\":\"units\",\"op\":\"gte\",\"value\":5}]'; omit to keep coverage unknown")
args = parser.parse_args()
proposals = read_json(args.proposals)
candidate = next((value for value in proposals["candidates"] if value["candidate_id"] == args.candidate_id), None)
if not candidate:
    parser.error("candidate ID not found")
source_text = Path(proposals["source_file"]).read_text(encoding="utf-8")
rule = approve_candidate(candidate, source_text, title=args.title, citation=args.citation,
    status=args.status, coverage_conditions=args.coverage_conditions,
    effective_date=args.effective_date, exemptions=args.exemptions, penalty=args.penalty,
    coverage_spec=json.loads(args.coverage_json) if args.coverage_json else None)
registry = ROOT / "sources" / "approved_new_laws.json"
rules = read_json(registry) if registry.exists() else []
if any(existing["team_rule_id"] == rule["team_rule_id"] for existing in rules):
    parser.error("candidate is already approved")
rules.append(rule)
write_json(registry, rules)
print(f"Recorded reviewed rule {rule['team_rule_id']}; run npm run pipeline to regenerate affected passports")
