import csv
import tempfile
import unittest
from pathlib import Path

from engine.portfolio import assess_rule, connect, impact, import_csv, passport, portfolio_stats


class PortfolioTests(unittest.TestCase):
    def test_stream_import_upsert_and_boundary_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "properties.csv"
            columns = ["address_id", "street_address", "postal_city", "state", "zip", "year_built", "units", "source_dataset", "retrieved_at", "legal_city"]
            rows = [
                ["a", "1 Test St", "Dorchester", "MA", "02101", "1900", "4", "test", "2026-10-03", ""],
                ["b", "2 Test St", "Hoboken", "NJ", "07030", "2000", "5", "test", "2026-10-03", "Hoboken"],
                ["c", "3 Test St", "Unknownville", "NJ", "07030", "", "", "test", "2026-10-03", ""],
            ]
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(rows)
            database = connect(root / "portfolio.sqlite")
            self.assertEqual(3, import_csv(database, path, batch_size=2))
            self.assertEqual(3, portfolio_stats(database)["properties"])
            self.assertEqual(1, portfolio_stats(database)["legal_city_unresolved"])
            self.assertEqual(3, portfolio_stats(database)["owner_type_missing"])
            self.assertEqual(["a"], list(impact(database, "Boston, MA", page_size=1)))
            self.assertEqual(["b"], list(impact(database, "Hoboken, NJ", page_size=1)))
            self.assertEqual(["b", "c"], list(impact(database, "NJ", page_size=1)))
            self.assertEqual("legal_boundary_unverified", database.execute("SELECT jurisdiction_evidence FROM property WHERE address_id='c'").fetchone()[0])
            self.assertEqual(3, import_csv(database, path, batch_size=2))
            self.assertEqual(3, database.execute("SELECT count(*) FROM property").fetchone()[0])
            self.assertEqual(3, import_csv(database, path, assume_sample_city=True))
            self.assertEqual(["c"], list(impact(database, "Unknownville, NJ")))
            self.assertIn("assumption", database.execute("SELECT jurisdiction_evidence FROM property WHERE address_id='c'").fetchone()[0])
            reviewed_rule = {
                "team_rule_id": "NEW-test", "jurisdiction": "Hoboken, NJ",
                "level": "city", "status": "in_force", "effective_date": None,
                "category": "security_deposits", "source_doc_id": "INTAKE-test",
                "citation": "Section 1", "source_url": "https://example.org/law",
                "quoted_span": "A landlord shall not demand excessive security deposits.",
                "extraction_mode": "generic_candidate_reviewed",
                "coverage_spec": [{"field": "units", "op": "gte", "value": 5}],
            }
            self.assertEqual({"jurisdiction_unverified": 1}, assess_rule(database, reviewed_rule, "2026-10-03")["results"])
            self.assertEqual([], passport(database, "b", [reviewed_rule], "2026-10-03")["rules"])
            self.assertTrue(passport(database, "b", [reviewed_rule], "2026-10-03")["city_boundary_needs_verification"])
            self.assertEqual(0.0, passport(database, "b", [reviewed_rule], "2026-10-03")["jurisdiction"]["confidence"])


if __name__ == "__main__":
    unittest.main()
