import unittest

from engine.source_monitor import observe


class SourceMonitorTests(unittest.TestCase):
    def test_baseline_change_and_no_change(self):
        args = ("D001", "2026-10-03T00:00:00Z", "https://example.org/law", "text/plain")
        first, event = observe({}, args[0], b"old law", *args[1:])
        self.assertEqual("baseline", event["status"])
        second, event = observe(first, args[0], b"old law", *args[1:])
        self.assertEqual("unchanged", event["status"])
        _, event = observe(second, args[0], b"new law", *args[1:])
        self.assertEqual("changed", event["status"])
        self.assertEqual("needs_human_review", event["review_status"])


if __name__ == "__main__":
    unittest.main()
