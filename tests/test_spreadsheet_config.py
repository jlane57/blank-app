import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import spreadsheet_config


class SpreadsheetConfigTests(unittest.TestCase):
    def test_environment_secret_is_used_when_streamlit_secret_is_missing(self):
        fake_streamlit = SimpleNamespace(secrets={})
        with patch("spreadsheet_config.st", fake_streamlit), patch.dict(
            os.environ, {"SPREADSHEET_ID": "github-preview-id"}, clear=False
        ):
            self.assertEqual(
                spreadsheet_config.get_required_secret("SPREADSHEET_ID"),
                "github-preview-id",
            )

    def test_streamlit_secret_takes_precedence_over_environment_secret(self):
        fake_streamlit = SimpleNamespace(secrets={"SPREADSHEET_ID": "streamlit-id"})
        with patch("spreadsheet_config.st", fake_streamlit), patch.dict(
            os.environ, {"SPREADSHEET_ID": "github-preview-id"}, clear=False
        ):
            self.assertEqual(
                spreadsheet_config.get_required_secret("SPREADSHEET_ID"),
                "streamlit-id",
            )

    def test_spreadsheet_errors_redact_export_url(self):
        self.assertEqual(
            spreadsheet_config.format_spreadsheet_error(
                "failed https://docs.google.com/spreadsheets/d/private-id/export"
            ),
            "failed https://docs.google.com/spreadsheets/d/[redacted]/export",
        )

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

    def test_spreadsheet_id_accepts_quotes_added_to_secret_value(self):
        with patch(
            "spreadsheet_config.get_required_secret",
            return_value=' "configured-id" ',
        ):
            self.assertEqual(spreadsheet_config.get_spreadsheet_id(), "configured-id")

    def test_spreadsheet_id_rejects_full_url(self):
        with patch(
            "spreadsheet_config.get_required_secret",
            return_value="https://docs.google.com/spreadsheets/d/configured-id/edit",
        ):
            with self.assertRaisesRegex(ValueError, "only the Google Sheets document ID"):
                spreadsheet_config.get_spreadsheet_id()

    def test_missing_spreadsheet_secret_stops_with_configuration_error(self):
        stop = Mock(side_effect=RuntimeError("stopped"))
        fake_streamlit = SimpleNamespace(
            secrets={},
            error=Mock(),
            stop=stop,
        )
        with patch("spreadsheet_config.st", fake_streamlit), patch.dict(
            os.environ, {}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "stopped"):
                spreadsheet_config.get_spreadsheet_id()

        fake_streamlit.error.assert_called_once_with(
            "Set SPREADSHEET_ID in Streamlit secrets or the environment to use this app feature."
        )
