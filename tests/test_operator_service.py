import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import operator_service


class OperatorServiceTests(unittest.TestCase):
    def test_new_property_is_persisted_and_city_rules_are_withheld(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(operator_service, "DATABASE", Path(directory) / "portfolio.sqlite"):
            result = operator_service.process({"action": "import_property", "property": {
                "address_id": "DEMO-TEST", "street_address": "1 Test Street",
                "postal_city": "Dorchester", "state": "MA", "zip": "02101", "units": "6",
            }})
            self.assertTrue(result["saved"])
            self.assertEqual(501, result["portfolio_properties"])
            self.assertTrue(result["passport"]["city_boundary_needs_verification"])
            self.assertEqual("legal_boundary_unverified", result["passport"]["property"]["jurisdiction_evidence"])
            self.assertFalse(any(rule["team_rule_id"].startswith("BOSTON-") for rule in result["passport"]["rules"]))
            again = operator_service.process({"action": "import_property", "property": {
                "address_id": "DEMO-TEST", "street_address": "1 Updated Street",
                "postal_city": "Dorchester", "state": "MA", "zip": "02101", "units": "6",
            }})
            self.assertEqual(501, again["portfolio_properties"])

    def test_unfamiliar_source_extracts_then_reviews_and_assesses(self):
        text = "A landlord of a building with five or more units shall not demand more than one month's rent as a security deposit."
        base = {"action": "preview_law", "source_text": text, "jurisdiction": "MA",
                "source_url": "https://example.org/ordinance", "retrieved_at": "2026-10-04"}
        with tempfile.TemporaryDirectory() as directory, patch.object(operator_service, "DATABASE", Path(directory) / "portfolio.sqlite"):
            extracted = operator_service.process(base)
            self.assertEqual(1, extracted["candidate_count"])
            self.assertEqual("needs_human_review", extracted["review_status"])
            reviewed = operator_service.process({**base, "review": {
                "title": "Test deposit cap", "citation": "Section 1", "status": "in_force",
                "coverage_conditions": "At least five units", "coverage_spec": [
                    {"field": "units", "op": "gte", "value": 5},
                ],
            }})
            self.assertEqual("reviewed_preview_not_published", reviewed["review_status"])
            self.assertEqual(110, reviewed["impact"]["candidates"])
            self.assertIn("unknown", reviewed["impact"]["results"])
            self.assertIn("applies", reviewed["impact"]["results"])


if __name__ == "__main__":
    unittest.main()
