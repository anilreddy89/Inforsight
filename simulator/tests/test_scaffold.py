import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import project_identity  # noqa: E402


class ScaffoldTest(unittest.TestCase):
    def test_project_identity_declares_synthetic_only_data(self) -> None:
        identity = project_identity()
        self.assertEqual(identity["name"], "Inforsight")
        self.assertEqual(identity["tagline"], "See Risk. Shape Action.")
        self.assertEqual(identity["data_policy"], "synthetic-only")


if __name__ == "__main__":
    unittest.main()
