import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import site_status


class SiteStatusTests(unittest.TestCase):
    def test_saved_settings_survive_reload_without_automatic_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / "site_status.json"
            with patch.object(site_status, "STATUS_FILE", status_file):
                site_status.save_site_status(
                    False,
                    "Maintenance",
                    True,
                    "Meet results will be posted tonight.",
                )
                saved = site_status.get_site_status()
                reloaded = site_status.get_site_status()

            self.assertEqual(saved, reloaded)
            self.assertFalse(reloaded["enabled"])
            self.assertTrue(reloaded["banner_enabled"])
            self.assertEqual(reloaded["offline_message"], "Maintenance")
            self.assertEqual(
                reloaded["banner_message"],
                "Meet results will be posted tonight.",
            )

    def test_status_file_contains_all_persistent_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / "site_status.json"
            with patch.object(site_status, "STATUS_FILE", status_file):
                site_status.save_site_status(True, "Offline", False, "Banner")
                raw = json.loads(status_file.read_text(encoding="utf-8"))

            self.assertEqual(
                set(raw),
                {"enabled", "offline_message", "banner_enabled", "banner_message"},
            )

    def test_legacy_status_defaults_banner_off_without_changing_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / "site_status.json"
            status_file.write_text(
                json.dumps({"enabled": False, "offline_message": "Down"}),
                encoding="utf-8",
            )
            with patch.object(site_status, "STATUS_FILE", status_file):
                status = site_status.get_site_status()

            self.assertFalse(status["enabled"])
            self.assertFalse(status["banner_enabled"])


if __name__ == "__main__":
    unittest.main()
