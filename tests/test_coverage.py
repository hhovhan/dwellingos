import unittest

from engine.coverage import check


class CoverageTests(unittest.TestCase):
    def test_three_valued_coverage(self):
        spec = [{"field": "units", "op": "gte", "value": 5}]
        self.assertEqual((True, []), check(spec, {"units": 6}))
        self.assertEqual((False, []), check(spec, {"units": 4}))
        self.assertEqual((None, ["units"]), check(spec, {"units": None}))
        self.assertEqual((None, ["coverage_predicate_not_encoded"]), check(None, {"units": 6}))
        self.assertEqual((True, []), check([], {}))


if __name__ == "__main__":
    unittest.main()
