import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_updates.py"
SPEC = importlib.util.spec_from_file_location("check_updates", SCRIPT)
CHECK_UPDATES = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECK_UPDATES)


class UpdateCheckTests(unittest.TestCase):
    def test_semantic_versions_compare_numerically(self):
        self.assertGreater(
            CHECK_UPDATES.parse_version("2.10.0"),
            CHECK_UPDATES.parse_version("2.9.9"),
        )
        with self.assertRaises(CHECK_UPDATES.UpdateCheckError):
            CHECK_UPDATES.parse_version("version two")

    def test_missing_or_elapsed_state_is_due(self):
        now = datetime(2026, 7, 24, tzinfo=timezone.utc)
        self.assertTrue(CHECK_UPDATES.is_due({}, now))
        self.assertTrue(
            CHECK_UPDATES.is_due(
                {"nextCheckAt": CHECK_UPDATES.format_time(now - timedelta(seconds=1))},
                now,
            )
        )
        self.assertFalse(
            CHECK_UPDATES.is_due(
                {"nextCheckAt": CHECK_UPDATES.format_time(now + timedelta(seconds=1))},
                now,
            )
        )

    def test_successful_schedule_is_between_14_and_17_days(self):
        now = datetime(2026, 7, 24, tzinfo=timezone.utc)
        with mock.patch.object(CHECK_UPDATES.secrets, "randbelow", return_value=86400):
            scheduled = CHECK_UPDATES.next_successful_check(now)
        self.assertEqual(scheduled, now + timedelta(days=15))

    def test_state_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            expected = {"nextCheckAt": "2026-08-07T00:00:00Z"}
            CHECK_UPDATES.save_state(path, expected)
            self.assertEqual(CHECK_UPDATES.load_state(path), expected)
            self.assertEqual(json.loads(path.read_text()), expected)


if __name__ == "__main__":
    unittest.main()
