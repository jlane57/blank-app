import unittest
from unittest.mock import Mock, patch

import spreadsheet_storage


class SpreadsheetStorageTests(unittest.TestCase):
    @patch("spreadsheet_storage._service_account_credentials")
    def test_headers_use_bearer_access_token(self, get_credentials):
        get_credentials.return_value = Mock(token="access-token")

        self.assertEqual(
            spreadsheet_storage._headers(),
            {"Authorization": "Bearer access-token"},
        )

    @patch("spreadsheet_storage._service_account_credentials")
    def test_headers_reject_missing_access_token(self, get_credentials):
        get_credentials.return_value = Mock(token=None)

        with self.assertRaisesRegex(RuntimeError, "access token"):
            spreadsheet_storage._headers()


if __name__ == "__main__":
    unittest.main()
