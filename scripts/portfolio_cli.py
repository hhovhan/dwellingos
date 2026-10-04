"""Import additional properties and calculate a jurisdiction's impact set."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import OUTPUT, read_json
from engine.portfolio import assess_rule, connect, impact, import_csv, passport, portfolio_stats

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--database", type=Path, required=True)
subcommands = parser.add_subparsers(dest="command", required=True)
subcommands.add_parser("stats")
import_command = subcommands.add_parser("import")
import_command.add_argument("csv", type=Path)
import_command.add_argument("--assume-sample-city", action="store_true",
    help="Use postal city as a provisional legal city for the fixed challenge sample only")
impact_command = subcommands.add_parser("impact")
impact_command.add_argument("jurisdiction", help="State code or 'City, ST'")
impact_command.add_argument("--limit", type=int, default=20)
assess_command = subcommands.add_parser("assess")
assess_command.add_argument("rule_id")
assess_command.add_argument("--as-of", default="2026-10-01")
passport_command = subcommands.add_parser("passport")
passport_command.add_argument("address_id")
passport_command.add_argument("--as-of", default="2026-10-01")
args = parser.parse_args()
args.database.parent.mkdir(parents=True, exist_ok=True)
database = connect(args.database)
if args.command == "import":
    count = import_csv(database, args.csv, assume_sample_city=args.assume_sample_city)
    print(f"Imported or updated {count} properties")
elif args.command == "stats":
    import json
    print(json.dumps(portfolio_stats(database), indent=2))
elif args.command == "assess":
    rules = read_json(OUTPUT / "rules.json")["rules"]
    rule = next((value for value in rules if value["team_rule_id"] == args.rule_id), None)
    if not rule:
        parser.error("rule ID not found in output/rules.json")
    import json
    print(json.dumps(assess_rule(database, rule, args.as_of), indent=2))
elif args.command == "passport":
    import json
    rules = read_json(OUTPUT / "rules.json")["rules"]
    value = passport(database, args.address_id, rules, args.as_of)
    if not value:
        parser.error("property ID not found")
    print(json.dumps(value, indent=2))
else:
    if args.limit < 0:
        parser.error("--limit must be non-negative")
    count = 0
    examples = []
    for address_id in impact(database, args.jurisdiction):
        count += 1
        if len(examples) < args.limit:
            examples.append(address_id)
    print(f"Jurisdiction: {args.jurisdiction}; indexed candidate properties: {count}")
    print("Example IDs: " + ", ".join(examples))
