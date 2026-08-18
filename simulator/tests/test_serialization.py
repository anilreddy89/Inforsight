import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator.__main__ import main  # noqa: E402


class SerializationCliTest(unittest.TestCase):
    def test_cli_stdout_is_jsonl_and_diagnostics_use_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["--seed", "7", "--policy-count", "4"])

        self.assertEqual(result, 0)
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertGreaterEqual(len(events), 4)
        self.assertTrue(all("event_type" in event for event in events))
        self.assertIn("generation_provenance=", stderr.getvalue())
        self.assertNotIn("generation_provenance", stdout.getvalue())

    def test_cli_file_output_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            first = Path(temporary_directory) / "first.jsonl"
            second = Path(temporary_directory) / "second.jsonl"
            for output in (first, second):
                with contextlib.redirect_stderr(io.StringIO()):
                    result = main(
                        [
                            "--seed",
                            "17",
                            "--policy-count",
                            "8",
                            "--output",
                            str(output),
                        ]
                    )
                self.assertEqual(result, 0)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_cli_refuses_to_overwrite_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "events.jsonl"
            output.write_text("keep me", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["--seed", "3", "--output", str(output)])
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me")

    def test_cli_rejects_nonpositive_policy_count(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--seed", "3", "--policy-count", "0"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
