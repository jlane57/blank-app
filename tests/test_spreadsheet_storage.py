import unittest
from unittest.mock import Mock, patch

import spreadsheet_storage


class SpreadsheetStorageTests(unittest.TestCase):
    def test_missing_google_auth_uses_local_fallback(self):
        with patch.object(
            spreadsheet_storage,
            "get_configured_secret",
            return_value='{"client_email":"x","private_key":"x","token_uri":"x"}',
        ), patch.object(
            spreadsheet_storage,
            "_service_account_credentials",
            side_effect=RuntimeError(
                "Spreadsheet storage requires the google-auth dependency."
            ),
        ):
            self.assertFalse(spreadsheet_storage.storage_configured())

    @patch("spreadsheet_storage._service_account_credentials")
    def test_headers_use_bearer_access_token(self, get_credentials):
        get_credentials.return_value = Mock(token="access-token")

        self.assertEqual(
            spreadsheet_storage._headers(),
            {"Authorization": "Bearer " + "access-token"},
        )

    @patch("spreadsheet_storage._service_account_credentials")
    def test_headers_reject_missing_access_token(self, get_credentials):
        get_credentials.return_value = Mock(token=None)

        with self.assertRaisesRegex(RuntimeError, "access token"):
            spreadsheet_storage._headers()


if __name__ == "__main__":
    unittest.main()
