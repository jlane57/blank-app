import unittest
from unittest.mock import Mock, patch

import requests

from bug_reports import submit_bug_report


class BugReportTests(unittest.TestCase):
    @patch("bug_reports.requests.post")
    def test_submission_posts_trimmed_report_and_accepts_success(self, post):
        response = Mock()
        response.json.return_value = {"ok": True}
        post.return_value = response

        submit_bug_report("  The time is wrong.  ", " https://example.test/exec ", " token ")

        post.assert_called_once_with(
            "https://example.test/exec",
            json={"secret": "token", "message": "The time is wrong."},
            timeout=15,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("bug_reports.requests.post")
    def test_submission_surfaces_service_rejection(self, post):
        response = Mock()
        response.json.return_value = {"ok": False}
        post.return_value = response

        with self.assertRaisesRegex(RuntimeError, "could not accept"):
            submit_bug_report("Something broke", "https://example.test/exec", "token")

    @patch("bug_reports.requests.post")
    def test_submission_rejects_empty_report_without_request(self, post):
        with self.assertRaisesRegex(ValueError, "Enter a description"):
            submit_bug_report("  ", "https://example.test/exec", "token")
        post.assert_not_called()

    @patch("bug_reports.requests.post")
    def test_submission_propagates_http_failures(self, post):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("service unavailable")
        post.return_value = response

        with self.assertRaisesRegex(requests.HTTPError, "service unavailable"):
            submit_bug_report("Something broke", "https://example.test/exec", "token")


if __name__ == "__main__":
    unittest.main()
