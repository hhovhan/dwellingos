import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PortfolioCliTests(unittest.TestCase):
    def test_invalid_scenario_date_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/portfolio_cli.py"),
                 "--database", str(Path(directory) / "portfolio.sqlite"),
                 "passport", "A0013", "--as-of", "2026-13-99"],
                capture_output=True, text=True, cwd=ROOT,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn("must be a valid YYYY-MM-DD date", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
