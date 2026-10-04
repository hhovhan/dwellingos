import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.common import CORPUS, OUTPUT, PACK, PUBLIC, VALID_RESULTS, normalize, read_csv, read_json, source_body
from engine.evaluator import evaluate, resolve_jurisdiction


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addresses = read_csv(PACK / "data" / "sample_addresses.csv")
        cls.rules = read_json(OUTPUT / "rules.json")["rules"]
        cls.lookups = read_json(OUTPUT / "lookups.json")["lookups"]

    def test_all_500_addresses_and_unique_ids(self):
        ids = [row["address_id"] for row in self.addresses]
        self.assertEqual(500, len(ids))
        self.assertEqual(500, len(set(ids)))
        self.assertEqual(set(ids), set(self.lookups))

    def test_zip_state_conflicts_are_exposed_not_silently_trusted(self):
        passports = {item["id"]: item for item in read_json(PUBLIC / "passports.json")["passports"]}
        flagged = [item for item in passports.values() if item["zip_state_conflict"]]
        self.assertEqual(27, len(flagged))
        self.assertTrue(passports["A0003"]["zip_state_conflict"])
        self.assertFalse(passports["A0013"]["zip_state_conflict"])
        for item in flagged:
            self.assertTrue(any(gap["field"] == "zip_state_conflict" and gap["severity"] == "blocking" for gap in item["missing"]))

    def test_every_quote_is_verbatim_source_evidence(self):
        for rule in self.rules:
            if rule["source_doc_id"].startswith("S-"):
                supplemental = read_json(ROOT / "sources" / "verified_supplemental.json")
                source = next(item for item in supplemental if item["doc_id"] == rule["source_doc_id"])
                self.assertEqual(source["quoted_span"], rule["quoted_span"])
                continue
            source_path = (ROOT / "sources" / "recovered" / f"{rule['source_doc_id']}.txt") if rule["source_doc_id"].startswith("REC-") else (CORPUS / "text" / f"{rule['source_doc_id']}.txt")
            source = source_path.read_text(encoding="utf-8", errors="replace")
            self.assertIn(rule["quoted_span"], normalize(source_body(source)), rule["team_rule_id"])
            self.assertGreaterEqual(len(rule["quoted_span"]), 20)

    def test_unpublished_automatic_candidate_queue_is_source_bound(self):
        queue = read_json(OUTPUT / "auto_candidates.json")
        self.assertEqual("unpublished_automatic_review_queue", queue["status"])
        self.assertGreaterEqual(queue["count"], 150)
        self.assertEqual(queue["count"], len(queue["candidates"]))
        self.assertEqual(queue["count"], len({item["candidate_id"] for item in queue["candidates"]}))
        for item in queue["candidates"]:
            source = (CORPUS / "text" / f'{item["source_doc_id"]}.txt').read_text(encoding="utf-8", errors="replace")
            self.assertIn(item["quoted_span"], normalize(source_body(source)))
            self.assertEqual("needs_human_review", item["review_status"])

    def test_results_use_allowed_vocabulary(self):
        for evaluations in self.lookups.values():
            for value in evaluations:
                self.assertIn(value["result"], VALID_RESULTS)

    def test_browser_decision_tables_match_python_engine(self):
        passports = read_json(PUBLIC / "passports.json")["passports"]
        rows = {row["address_id"]: row for row in self.addresses}
        rules = {rule["team_rule_id"]: rule for rule in self.rules}
        for passport in passports:
            row = rows[passport["id"]]
            for rendered in passport["rules"]:
                rule = rules[rendered["team_rule_id"]]
                table = rendered["decision_table"]
                candidates = [(row, table["default"])]
                if "scenario_field" in table:
                    candidates.extend(({**row, table["scenario_field"]: value}, dates)
                                      for value, dates in table["choices"].items())
                for facts, dates in candidates:
                    for key, when in (("before", "0001-01-01"),
                                      ("active", rule.get("valid_through") or "2026-10-01"),
                                      ("after", "9999-12-31")):
                        expected = evaluate(rule, facts, when)
                        actual = dates[key]
                        self.assertEqual(expected["result"] if expected else "excluded", actual["result"])
                        if expected:
                            self.assertEqual(expected["missing_coverage_facts"], actual["missing_coverage_facts"])
        sf_passport = next(item for item in passports if item["legal_city"] == "San Francisco")
        sf_state = next(item for item in sf_passport["rules"] if item["source_doc_id"] == "D024")
        self.assertEqual({"start": "2026-03-01", "end": "2027-02-28"}, sf_state["decision_table"]["scenario_window"])
        self.assertEqual("superseded", sf_state["decision_table"]["choices"]["covered"]["active"]["result"])

    def test_time_bounded_rates_do_not_survive_their_source_window(self):
        profiles = {rule["source_doc_id"]: rule for rule in self.rules if rule["source_doc_id"] in {"D042", "D080", "D083"}}
        la = next(row for row in self.addresses if row["postal_city"] == "Los Angeles")
        sf = next(row for row in self.addresses if row["postal_city"] == "San Francisco")
        self.assertEqual("unknown", evaluate(profiles["D042"], la, "2026-10-01")["result"])
        self.assertEqual("unknown", evaluate(profiles["D080"], sf, "2027-03-01")["result"])
        self.assertEqual("unknown", evaluate(profiles["D083"], sf, "2027-03-01")["result"])
        self.assertEqual("unknown", evaluate(profiles["D080"], sf, "2026-10-01")["result"])

    def test_sf_stricter_city_rule_requires_verified_coverage(self):
        state = next(rule for rule in self.rules if rule["source_doc_id"] == "D024")
        city = next(rule for rule in self.rules if rule["source_doc_id"] == "D080")
        sf = next(row for row in self.addresses if row["postal_city"] == "San Francisco")
        self.assertEqual("unknown", evaluate(state, sf, "2026-10-01")["result"])
        self.assertEqual("unknown", evaluate(city, sf, "2026-10-01")["result"])
        covered = dict(sf, rent_control_status="covered")
        self.assertEqual("superseded", evaluate(state, covered, "2026-10-01")["result"])
        self.assertEqual("applies", evaluate(city, covered, "2026-10-01")["result"])
        self.assertIsNone(evaluate(city, dict(sf, rent_control_status="exempt"), "2026-10-01"))
        self.assertEqual("unknown", evaluate(city, covered, "2027-03-01")["result"])

    def test_city_aliases(self):
        dorchester = next(row for row in self.addresses if row["postal_city"] == "Dorchester")
        san_ysidro = next(row for row in self.addresses if row["postal_city"] == "San Ysidro")
        self.assertEqual("Boston", resolve_jurisdiction(dorchester)["legal_city"])
        self.assertEqual("San Diego", resolve_jurisdiction(san_ysidro)["legal_city"])

    def test_t1_california_temporal_boundary(self):
        rule = next(r for r in self.rules if r["team_rule_id"] == "CA-ALG-01")
        ca = next(row for row in self.addresses if row["state"] == "CA")
        self.assertEqual("not_yet_effective", evaluate(rule, ca, "2025-12-31")["result"])
        self.assertEqual("applies", evaluate(rule, ca, "2026-01-02")["result"])

    def test_t3_new_jersey_temporal_boundary(self):
        rule = next(r for r in self.rules if r["team_rule_id"] == "NJ-ALG-01")
        nj = next(row for row in self.addresses if row["state"] == "NJ")
        self.assertEqual("not_yet_effective", evaluate(rule, nj, "2026-10-01")["result"])
        self.assertEqual("applies", evaluate(rule, nj, "2027-07-02")["result"])

    def test_pending_massachusetts_rules(self):
        for rule_id in ("MA-ALG-P1", "MA-ALG-P2"):
            rule = next(r for r in self.rules if r["team_rule_id"] == rule_id)
            ma = next(row for row in self.addresses if row["state"] == "MA")
            self.assertEqual("pending", evaluate(rule, ma, "2026-10-01")["result"])

    def test_jurisdiction_boundary(self):
        sf_rule = next(r for r in self.rules if r["team_rule_id"] == "SF-ALG-01")
        sf = next(row for row in self.addresses if row["postal_city"] == "San Francisco")
        la = next(row for row in self.addresses if row["postal_city"] == "Los Angeles")
        self.assertEqual("applies", evaluate(sf_rule, sf, "2026-10-01")["result"])
        self.assertIsNone(evaluate(sf_rule, la, "2026-10-01"))

    def test_recovered_city_rules_are_evidence_gated(self):
        newark = next(rule for rule in self.rules if rule["team_rule_id"] == "NEWARK-RENT-01")
        san_diego = next(rule for rule in self.rules if rule["team_rule_id"] == "SD-INCOME-01")
        newark_property = {"postal_city": "Newark", "legal_city": "Newark", "state": "NJ"}
        san_diego_property = {"postal_city": "San Diego", "legal_city": "San Diego", "state": "CA"}
        self.assertEqual("unknown", evaluate(newark, newark_property, "2026-10-01")["result"])
        self.assertEqual("applies", evaluate(newark, dict(newark_property, rent_control_status="covered"), "2026-10-01")["result"])
        self.assertIsNone(evaluate(newark, dict(newark_property, rent_control_status="exempt"), "2026-10-01"))
        self.assertEqual("unknown", evaluate(san_diego, san_diego_property, "2026-10-01")["result"])
        self.assertEqual("applies", evaluate(san_diego, dict(san_diego_property, owner_occupied_shared_kitchen_or_bath="no"), "2026-10-01")["result"])
        self.assertIsNone(evaluate(san_diego, dict(san_diego_property, owner_occupied_shared_kitchen_or_bath="yes"), "2026-10-01"))

    def test_change_tracking_expected_sets(self):
        changes = read_json(OUTPUT / "changes.json")
        self.assertEqual(250, len(changes["T1"]["affected_address_ids"]))
        self.assertEqual(90, len(changes["T2"]["affected_address_ids"]))
        self.assertEqual(140, len(changes["T3"]["affected_address_ids"]))
        self.assertEqual(90, len(changes["T3"]["conflict_flag_address_ids"]))
        self.assertEqual(110, len(changes["T4"]["affected_address_ids"]))
        self.assertEqual([], changes["T5"]["affected_address_ids"])

    def test_required_rule_fields_and_unique_ids(self):
        required = {"team_rule_id", "jurisdiction", "level", "category", "status", "title", "requirement", "citation", "source_url", "quoted_span"}
        ids = []
        for rule in self.rules:
            self.assertTrue(required.issubset(rule), rule.get("team_rule_id"))
            self.assertIn(rule["level"], {"state", "city"})
            self.assertIn(rule["status"], {"in_force", "not_yet_effective", "pending", "failed"})
            ids.append(rule["team_rule_id"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_failed_rules_never_enter_live_lookups(self):
        failed = {rule["team_rule_id"] for rule in self.rules if rule["status"] == "failed"}
        returned = {value["team_rule_id"] for values in self.lookups.values() for value in values}
        self.assertTrue(failed.isdisjoint(returned))

    def test_missing_property_facts_never_create_rent_certainty(self):
        row = next(row for row in self.addresses if not row["year_built"] or not row["units"])
        candidates = [rule for rule in self.rules if rule["category"] in {"rent_increase_limits", "just_cause_eviction"}]
        for rule in candidates:
            value = evaluate(rule, row, "2026-10-01")
            if value:
                self.assertNotEqual("applies", value["result"])

    def test_conduct_rules_can_resolve_without_building_facts(self):
        ca = next(row for row in self.addresses if row["state"] == "CA")
        rule = next(rule for rule in self.rules if rule["team_rule_id"] == "CA-ALG-01")
        self.assertEqual("applies", evaluate(rule, ca, "2026-10-01")["result"])

    def test_quality_report_contract(self):
        report = read_json(OUTPUT / "quality_report.json")
        self.assertEqual(500, report["properties"])
        self.assertEqual(1.0, report["citation_completeness"])
        self.assertEqual(1.0, report["verbatim_evidence_completeness"])
        self.assertEqual(500, report["properties_with_at_least_one_result"])

    def test_every_live_lookup_matches_its_jurisdiction(self):
        from engine.evaluator import jurisdiction_matches
        rules = {rule["team_rule_id"]: rule for rule in self.rules}
        addresses = {row["address_id"]: row for row in self.addresses}
        for address_id, values in self.lookups.items():
            jurisdiction = resolve_jurisdiction(addresses[address_id])
            for value in values:
                self.assertTrue(jurisdiction_matches(rules[value["team_rule_id"]], jurisdiction))

    def test_every_passport_has_exactly_six_category_summaries(self):
        passports = read_json(PUBLIC / "passports.json")["passports"]
        expected = {"rent_increase_limits", "just_cause_eviction", "security_deposits", "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting"}
        for passport in passports:
            self.assertEqual(expected, {value["category"] for value in passport["categories"]})

    def test_link_only_sources_have_explicit_dispositions(self):
        gaps = read_json(OUTPUT / "source_gap_register.json")["gaps"]
        self.assertEqual(33, len(gaps))
        self.assertTrue(all(gap["disposition"] for gap in gaps))
        self.assertEqual(1, sum(gap["disposition"] == "official_source_capture_blocked" for gap in gaps))

    def test_california_reviewed_numeric_rules(self):
        by_doc_category = {(rule["source_doc_id"], rule["category"]): rule for rule in self.rules}
        self.assertEqual("Lesser of 5% + cost of living or 10%", by_doc_category[("D024", "rent_increase_limits")]["key_value"])
        self.assertEqual("Generally one month's rent", by_doc_category[("D025", "security_deposits")]["key_value"])
        self.assertEqual("1.0%", by_doc_category[("D008", "rent_increase_limits")]["key_value"])
        self.assertEqual("3% through 2026-06-30", by_doc_category[("D042", "rent_increase_limits")]["key_value"])
        self.assertEqual("1.6%", by_doc_category[("D080", "rent_increase_limits")]["key_value"])
        self.assertEqual("Lower of 3% or 80% of CPI change", by_doc_category[("D085", "rent_increase_limits")]["key_value"])

    def test_california_reviewed_sources_have_review_status(self):
        reviewed_docs = {"D001", "D003", "D005", "D006", "D007", "D008", "D009", "D016", "D022", "D023", "D024", "D025", "D026", "D027", "D040", "D041", "D042", "D073", "D076", "D078", "D079", "D080", "D081", "D083", "D085"}
        for rule in self.rules:
            if rule["source_doc_id"] in reviewed_docs:
                self.assertEqual("california_source_reviewed", rule["review_status"])

    def test_california_algorithmic_rules_and_conflicts(self):
        by_id = {rule["team_rule_id"]: rule for rule in self.rules}
        self.assertEqual("2026-01-01", by_id["CA-ALG-01"]["effective_date"])
        berkeley = next(rule for rule in self.rules if rule["source_doc_id"] == "D001")
        self.assertEqual("2026-03-01", berkeley["effective_date"])
        self.assertTrue(berkeley["conflict_flag"])
        self.assertEqual("2024-10-14", by_id["SF-ALG-01"]["effective_date"])

    def test_new_jersey_sources_are_reviewed_and_scoped(self):
        reviewed_docs = {"D036", "D065", "D066", "D067", "D068", "D069", "S-JC-ALG", "S-HOB-ALG"}
        for rule in self.rules:
            if rule["source_doc_id"] in reviewed_docs:
                self.assertEqual("new_jersey_source_reviewed", rule["review_status"])
        d067_categories = {rule["category"] for rule in self.rules if rule["source_doc_id"] == "D067"}
        self.assertEqual({"rent_increase_limits", "just_cause_eviction", "security_deposits"}, d067_categories)

    def test_new_jersey_reviewed_values_and_operational_text(self):
        by_doc_category = {(rule["source_doc_id"], rule["category"]): rule for rule in self.rules}
        self.assertEqual("$50 through 2026; CPI adjustment begins in 2027", by_doc_category[("D066", "application_screening_fees")]["key_value"])
        self.assertEqual("Maximum 1.5 months' rent", by_doc_category[("D067", "security_deposits")]["key_value"])
        fair = by_doc_category[("D069", "algorithmic_rent_setting")]
        self.assertIn("unlawful", fair["quoted_span"].lower())
        self.assertEqual("2027-07-01", fair["effective_date"])
        self.assertTrue(fair["conflict_flag"])

    def test_new_jersey_explicit_unit_exemptions(self):
        base = dict(next(row for row in self.addresses if row["state"] == "NJ"))
        jersey_city = dict(base, postal_city="Jersey City", units="4")
        rent_rule = next(rule for rule in self.rules if rule["source_doc_id"] == "D036")
        self.assertIsNone(evaluate(rent_rule, jersey_city, "2026-10-01"))
        two_family = dict(base, units="2")
        fee_rule = next(rule for rule in self.rules if rule["source_doc_id"] == "D066")
        self.assertIsNone(evaluate(fee_rule, two_family, "2026-10-01"))
        larger = dict(base, units="8")
        self.assertEqual("unknown", evaluate(fee_rule, larger, "2026-10-01")["result"])

    def test_massachusetts_sources_are_reviewed_and_deduplicated(self):
        reviewed_docs = {"D010", "D011", "D012", "D014", "D029", "D031", "D045", "D046", "D048", "D049", "D050", "D051", "D052", "D053", "D058"}
        for rule in self.rules:
            if rule["source_doc_id"] in reviewed_docs:
                self.assertEqual("massachusetts_source_reviewed", rule["review_status"])
        self.assertFalse(any(rule["source_doc_id"] in {"D013", "D047", "D057"} for rule in self.rules))

    def test_massachusetts_reviewed_values_and_statuses(self):
        by_doc = {rule["source_doc_id"]: rule for rule in self.rules if rule["source_doc_id"].startswith("D")}
        self.assertEqual("Maximum one month's rent", by_doc["D052"]["key_value"])
        self.assertEqual("2025-08-01", by_doc["D052"]["effective_date"])
        self.assertEqual("14 days' notice for nonpayment", by_doc["D050"]["key_value"])
        self.assertEqual("pending", by_doc["D045"]["status"])
        self.assertEqual("pending", by_doc["D046"]["status"])
        self.assertEqual("failed", by_doc["D011"]["status"])

    def test_boston_fair_chance_policy_is_not_assumed_citywide(self):
        boston = next(row for row in self.addresses if resolve_jurisdiction(row)["legal_city"] == "Boston")
        rule = next(rule for rule in self.rules if rule["source_doc_id"] == "D010")
        value = evaluate(rule, boston, "2026-10-01")
        self.assertEqual("unknown", value["result"])
        self.assertIn("DND_or_BPDA_program_participation", value["missing_coverage_facts"])

    def test_boston_program_fact_changes_only_its_rule(self):
        boston = next(row for row in self.addresses if resolve_jurisdiction(row)["legal_city"] == "Boston")
        rule = next(rule for rule in self.rules if rule["source_doc_id"] == "D010")
        self.assertEqual("applies", evaluate(rule, dict(boston, DND_or_BPDA_program_participation="yes"), "2026-10-01")["result"])
        self.assertIsNone(evaluate(rule, dict(boston, DND_or_BPDA_program_participation="no"), "2026-10-01"))


if __name__ == "__main__":
    unittest.main()
