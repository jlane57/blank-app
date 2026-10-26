import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import news


class NewsTests(unittest.TestCase):
    def test_add_news_saves_newest_entry_first(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "news.json"
            with patch.object(news, "NEWS_FILE", path):
                news.add_news("Meet update", "Great race day.", "2026-10-20")
                news.add_news("Next update", "Practice details.", "2026-10-21")
                self.assertEqual(
                    [entry["headline"] for entry in news.get_news()],
                    ["Next update", "Meet update"],
                )

    def test_save_news_rejects_incomplete_entries(self):
        with self.assertRaises(ValueError):
            news.save_news([{"headline": "Missing body", "published": "2026-10-20"}])

    def test_news_sheet_rows_follow_expected_spreadsheet_columns(self):
        rows = news.news_sheet_rows(
            [
                {
                    "headline": "Header",
                    "author": "Coach",
                    "published": "2026-10-21",
                    "image": {"file_id": "abc123"},
                    "body": "Body text",
                }
            ]
        )
        self.assertEqual(
            rows[0],
            ["Header", "Author", "Date", "Image Link/ID", "Body"],
        )
        self.assertEqual(rows[1][3], "abc123")


if __name__ == "__main__":
    unittest.main()
