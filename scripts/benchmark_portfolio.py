"""Reproducible synthetic scale check; does not claim legal accuracy."""

import argparse
import csv
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.portfolio import assess_rule, connect, impact, import_csv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--count", type=int, default=100000)
args = parser.parse_args()
if not 1 <= args.count <= 20000000:
    parser.error("--count must be between 1 and 20,000,000")

with tempfile.TemporaryDirectory(prefix="dwellingos-benchmark-") as directory:
    root = Path(directory)
    csv_path = root / "properties.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["address_id", "street_address", "postal_city", "legal_city", "state", "zip", "year_built", "units", "source_dataset", "retrieved_at"])
        for index in range(args.count):
            city, state = (("Jersey City", "NJ") if index % 10 == 0 else ("Los Angeles", "CA"))
            writer.writerow([f"S{index:09d}", f"{index} Sample Street", city, city, state, "", "2000", "12", "synthetic benchmark", "2026-10-03"])
    database = connect(root / "portfolio.sqlite")
    start = time.perf_counter()
    imported = import_csv(database, csv_path)
    import_seconds = time.perf_counter() - start
    start = time.perf_counter()
    affected = sum(1 for _ in impact(database, "Jersey City, NJ"))
    impact_seconds = time.perf_counter() - start
    benchmark_rule = {
        "team_rule_id": "BENCHMARK", "jurisdiction": "Jersey City, NJ",
        "level": "city", "status": "in_force", "effective_date": None,
        "category": "security_deposits", "source_doc_id": "BENCHMARK",
        "extraction_mode": "generic_candidate_reviewed",
        "coverage_spec": [{"field": "units", "op": "gte", "value": 5}],
    }
    start = time.perf_counter()
    assessment = assess_rule(database, benchmark_rule, "2026-10-03")
    assessment_seconds = time.perf_counter() - start
    print(f"Synthetic properties: {imported}; indexed city candidates: {affected}")
    print(f"Import seconds: {import_seconds:.3f}; impact-query seconds: {impact_seconds:.3f}")
    print(f"Rule-assessment seconds: {assessment_seconds:.3f}; results: {assessment['results']}")
    print(f"SQLite bytes: {(root / 'portfolio.sqlite').stat().st_size}")
