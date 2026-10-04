import unittest
from pathlib import Path

from engine.evaluator import evaluate
from engine.law_intake import approve_candidate, extract_candidates


class LawIntakeTests(unittest.TestCase):
    def test_official_rate_page_extracts_clean_source_line(self):
        text = (Path(__file__).resolve().parents[1] / "realpage-starter-pack/corpus/text/D080.txt").read_text()
        values = extract_candidates(text, jurisdiction="San Francisco, CA",
            source_url="https://www.sf.gov/news--annual-rent-increase-3126-22827-announced",
            retrieved_at="2026-10-01")
        self.assertGreaterEqual(len(values), 1)
        self.assertEqual("rent_increase_limits", values[0]["category"])
        self.assertTrue(values[0]["quoted_span"].startswith("For rent-controlled units"))
        self.assertNotIn("Skip to main content", values[0]["quoted_span"])

    def test_unseen_document_produces_verbatim_unpublished_candidate(self):
        text = "A landlord shall not demand a security deposit greater than one month's rent.\n\nUnrelated heading and navigation text."
        values = extract_candidates(text, jurisdiction="Cambridge, MA",
            source_url="https://example.org/ordinance", retrieved_at="2026-10-03")
        self.assertEqual(1, len(values))
        self.assertEqual("security_deposits", values[0]["category"])
        self.assertIn(values[0]["quoted_span"], text)
        self.assertEqual("needs_human_review", values[0]["review_status"])

    def test_summary_without_action_does_not_become_rule(self):
        values = extract_candidates("The committee discussed security deposit rules and future hearings.",
            jurisdiction="NJ", source_url="https://example.org/hearing", retrieved_at="2026-10-03")
        self.assertEqual([], values)

    def test_rate_notice_and_rate_table_are_extracted(self):
        root = Path(__file__).resolve().parents[1] / "realpage-starter-pack/corpus/text"
        for doc, jurisdiction, target in [
            ("D008", "Berkeley, CA", "increase the 2025 permanent rent ceilings by 1.0%"),
            ("D083", "San Francisco, CA", "1.6% for March 1, 2026"),
        ]:
            text = (root / f"{doc}.txt").read_text()
            candidates = extract_candidates(text, jurisdiction=jurisdiction,
                source_url="https://example.org/rate-notice", retrieved_at="2026-10-01")
            self.assertTrue(any(c["category"] == "rent_increase_limits" and target in c["quoted_span"]
                                for c in candidates), doc)

    def test_bill_status_page_without_bill_text_is_not_an_operative_rule(self):
        text = (Path(__file__).resolve().parents[1] / "realpage-starter-pack/corpus/text/D046.txt").read_text()
        candidates = extract_candidates(text, jurisdiction="MA",
            source_url="https://malegislature.gov/Bills/194/S2983", retrieved_at="2026-10-01")
        self.assertEqual([], candidates)

    def test_review_gate_rejects_missing_evidence(self):
        text = "A landlord shall not demand a security deposit greater than one month's rent."
        candidate = extract_candidates(text, jurisdiction="MA",
            source_url="https://example.org/law", retrieved_at="2026-10-03")[0]
        with self.assertRaises(ValueError):
            approve_candidate(candidate, "different source", title="Deposit law", citation="Section 1",
                status="in_force", coverage_conditions="Residential rentals")
        rule = approve_candidate(candidate, text, title="Deposit law", citation="Section 1",
            status="in_force", coverage_conditions="Residential rentals")
        self.assertEqual("generic_candidate_reviewed", rule["extraction_mode"])

    def test_reviewed_new_law_flows_into_property_decision(self):
        text = "A landlord of a building with five or more units shall not demand more than one month's rent as a security deposit."
        candidate = extract_candidates(text, jurisdiction="Cambridge, MA",
            source_url="https://example.org/ordinance", retrieved_at="2026-10-03")[0]
        rule = approve_candidate(candidate, text, title="Deposit limit", citation="Section 1",
            status="not_yet_effective", effective_date="2026-11-01",
            coverage_conditions="Five or more units", coverage_spec=[{"field": "units", "op": "gte", "value": 5}])
        property_record = {"postal_city": "Cambridge", "legal_city": "Cambridge", "state": "MA", "units": 6,
                           "jurisdiction_evidence": "municipal_gis_verified"}
        self.assertEqual("not_yet_effective", evaluate(rule, property_record, "2026-10-31")["result"])
        self.assertEqual("applies", evaluate(rule, property_record, "2026-11-01")["result"])
        self.assertIsNone(evaluate(rule, dict(property_record, units=4), "2026-11-01"))
        self.assertEqual("unknown", evaluate(rule, dict(property_record, units=None), "2026-11-01")["result"])


if __name__ == "__main__":
    unittest.main()
