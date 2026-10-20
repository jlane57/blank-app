from io import BytesIO
import unittest

import openpyxl

from meet_import import (
    apply_approved_results,
    extract_result_rows,
    extract_rows,
    match_to_roster,
)


class MeetImportTests(unittest.TestCase):
    def test_csv_rows_match_roster_and_normalize_times(self):
        rows = extract_rows("meet.csv", b"Name,Time\nRunner One,0:16:25\n")
        extracted = extract_result_rows(rows)
        matched = match_to_roster(extracted, [{"name": "Runner One", "team": "B"}], "B")
        self.assertEqual(matched[0]["athlete"], "Runner One")
        self.assertEqual(matched[0]["time"], "16:25")
        self.assertEqual(matched[0]["status"], "Exact")

    def test_unmatched_or_invalid_rows_are_not_approved(self):
        rows = extract_rows("meet.csv", b"Name,Time\nUnknown,not-a-time\n")
        extracted = extract_result_rows(rows)
        matched = match_to_roster(extracted, [{"name": "Runner One", "team": "B"}], "B")
        self.assertEqual(matched[0]["status"], "Invalid time")
        self.assertEqual(matched[0]["athlete"], "")

    def test_export_rejects_overwriting_without_explicit_flag(self):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "2026"
        worksheet.append(["HHS Cross Country Data 2026"])
        worksheet.append(["", "", "Race Type >", "5K"])
        worksheet.append(["", "", "Location >", "Town"])
        worksheet.append(["", "", "Date >", "2026-10-01"])
        worksheet.append(["", "", "Meet Notes >", ""])
        worksheet.append(["", "", "Boys Place >", ""])
        worksheet.append(["", "", "Girls Place >", ""])
        worksheet.append(["Name", "Grade", "Team", "Meet One"])
        worksheet.append(["Runner One", 12, "B", ""])
        worksheet["D9"] = "16:25"
        stream = BytesIO()
        workbook.save(stream)
        with self.assertRaisesRegex(ValueError, "already has a result"):
            apply_approved_results(
                stream.getvalue(),
                2026,
                "B",
                {"existing_meet": "Meet One"},
                [{"athlete": "Runner One", "time": "17:00"}],
            )

    def test_group_matching_excludes_other_team(self):
        rows = extract_rows("meet.csv", b"Name,Time\nRunner One,16:19.347\n")
        matched = match_to_roster(
            extract_result_rows(rows),
            [{"name": "Runner One", "team": "G"}],
            "B",
        )
        self.assertEqual(matched[0]["status"], "Unmatched")
        self.assertEqual(matched[0]["athlete"], "")


if __name__ == "__main__":
    unittest.main()
