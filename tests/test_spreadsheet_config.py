import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import spreadsheet_config


class SpreadsheetConfigTests(unittest.TestCase):
    def test_spreadsheet_export_url_uses_configured_id(self):
        self.assertEqual(
            spreadsheet_config.get_spreadsheet_export_url("configured-id"),
            "https://docs.google.com/spreadsheets/d/configured-id/export",
        )

    def test_spreadsheet_id_comes_from_required_secret(self):
        with patch(
            "spreadsheet_config.get_required_secret",
            return_value="  configured-id  ",
        ) as get_required_secret:
            self.assertEqual(spreadsheet_config.get_spreadsheet_id(), "configured-id")

        get_required_secret.assert_called_once_with("SPREADSHEET_ID")

    def test_missing_spreadsheet_secret_stops_with_configuration_error(self):
        stop = Mock(side_effect=RuntimeError("stopped"))
        fake_streamlit = SimpleNamespace(
            secrets={},
            error=Mock(),
            stop=stop,
        )
        with patch("spreadsheet_config.st", fake_streamlit):
            with self.assertRaisesRegex(RuntimeError, "stopped"):
                spreadsheet_config.get_spreadsheet_id()

        fake_streamlit.error.assert_called_once_with(
            "Set SPREADSHEET_ID in Streamlit secrets to use this app feature."
        )
