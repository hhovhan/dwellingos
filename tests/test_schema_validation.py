import unittest

from engine.schema_validation import validate_rule


class SchemaValidationTests(unittest.TestCase):
    def test_missing_and_wrong_enum_are_rejected(self):
        schema = {"required": ["status", "quoted_span"],
                  "properties": {"status": {"enum": ["in_force", "pending"]},
                                 "quoted_span": {"type": "string", "minLength": 20}}}
        self.assertEqual([], validate_rule({"status": "pending", "quoted_span": "a long enough source quote"}, schema))
        self.assertEqual(["missing quoted_span", "status has invalid value"],
                         validate_rule({"status": "invented"}, schema))


if __name__ == "__main__":
    unittest.main()
