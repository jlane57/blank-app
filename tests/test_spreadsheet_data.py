from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO
import unittest

import openpyxl

from spreadsheet_data import (
    build_athlete_5k_chart_data,
    build_postseason_roster,
    build_postseason_season_chart_data,
    build_race_totals,
    find_year_sheet_layout,
    format_grade,
    format_meet_date,
    format_race_time,
    parse_meet_date,
    parse_race_time,
    parse_year_sheet,
    parse_workbook_years,
    sort_meets_by_date,
)


class SpreadsheetDataTests(unittest.TestCase):
    def test_race_times_preserve_minute_second_meaning(self):
        expected = Decimal(16 * 60 + 25)
        self.assertEqual(parse_race_time("16:25"), expected)
        self.assertEqual(parse_race_time("0:16:25"), expected)
        self.assertEqual(parse_race_time(time(0, 16, 25)), expected)
        self.assertEqual(parse_race_time(timedelta(minutes=16, seconds=25)), expected)
        self.assertEqual(format_race_time("16:25"), "16:25")
        self.assertEqual(format_race_time("0:16:25"), "16:25")
        self.assertEqual(format_race_time(time(0, 16, 25)), "16:25")
        self.assertEqual(format_race_time("60:00.1"), "60:00.1")
        self.assertEqual(format_race_time("16:25.100"), "16:25.1")
        self.assertEqual(format_race_time("16:25.120"), "16:25.12")
        self.assertEqual(format_race_time("16:25.000"), "16:25")
        self.assertEqual(format_race_time("16:25.1234"), "16:25.123")
        self.assertEqual(format_race_time("1:00:00"), "60:00")
        self.assertIsNone(parse_race_time(0.0114))
        self.assertIsNone(parse_race_time("0.0114"))

    def test_grade_and_excel_date_formatting(self):
        self.assertEqual(format_grade(12.0), "12")
        self.assertEqual(format_grade("12.0"), "12")
        self.assertEqual(format_grade("Senior"), "Senior")
        self.assertEqual(format_meet_date(date(2026, 10, 1)), "October 1")
        self.assertEqual(parse_meet_date(date(2026, 10, 1)), date(2026, 10, 1))
        self.assertEqual(
            parse_meet_date("2026-10-01"),
            date(2026, 10, 1),
        )
        ordered_meets = sort_meets_by_date(
            [
                {"name": "Later", "raw_date": date(2026, 10, 1)},
                {"name": "Undated", "raw_date": None},
                {"name": "Earlier", "raw_date": date(2026, 9, 1)},
            ]
        )
        self.assertEqual(
            [meet["name"] for meet in ordered_meets],
            ["Earlier", "Later", "Undated"],
        )

    def test_layout_and_results_skip_metadata_rows(self):
        rows = [
            [],
            ["Name", "Grade", "", "Meet One"],
            ["Meet Type", "", "", "Invitational"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2026, 10, 1)],
            ["Notes", "", "", "Notes here"],
            ["Team Place", "", "", 2],
            ["Runner One", 12.0, "", "16:25"],
        ]
        layout = find_year_sheet_layout(rows)
        self.assertIsNotNone(layout)
        assert layout is not None
        self.assertEqual(layout["team_place_row"], 6)
        self.assertEqual(layout["first_athlete_row"], 7)

        parsed = parse_year_sheet(rows, 2026, {(7, 3)})
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual([athlete["name"] for athlete in parsed["athletes"]], ["Runner One"])
        self.assertEqual(parsed["athletes"][0]["grade"], "12")
        result = parsed["results"][0]
        self.assertEqual(result["seconds"], Decimal(985))
        self.assertEqual(result["date"], "October 1")
        self.assertTrue(result["is_varsity"])

    def test_new_layout_reads_metadata_above_header_and_best_column(self):
        rows = [
            ["Harrison Cross Country Results 2026"],
            ["Meet Type >", "", "", "5K"],
            ["Meet Location >", "", "", "Amp"],
            ["Meet Date >", "", "", date(2026, 10, 1)],
            ["Meet Notes >", "", "", "Course was muddy"],
            ["Team Place >", "", "", "1st"],
            ["Name", "Grade", "Best", "Champ at the Amp"],
            ["Runner One", 12, "15:42", "16:25"],
        ]

        layout = find_year_sheet_layout(rows)
        self.assertIsNotNone(layout)
        assert layout is not None
        self.assertEqual(layout["header_row"], 6)
        self.assertEqual(layout["meet_type_row"], 1)
        self.assertEqual(layout["location_row"], 2)
        self.assertEqual(layout["date_row"], 3)
        self.assertEqual(layout["notes_row"], 4)
        self.assertEqual(layout["team_place_row"], 5)
        self.assertEqual(layout["first_athlete_row"], 7)

        parsed = parse_year_sheet(rows, 2026, {(7, 0)})
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["meets"][0]["type"], "5K")
        self.assertEqual(parsed["meets"][0]["location"], "Amp")
        self.assertEqual(parsed["meets"][0]["date"], "October 1")
        self.assertEqual(parsed["meets"][0]["notes"], "Course was muddy")
        self.assertEqual(parsed["meets"][0]["team_place"], "1st")
        self.assertEqual(parsed["athletes"][0]["name"], "Runner One")
        self.assertEqual(parsed["athletes"][0]["best"], "15:42")
        self.assertTrue(parsed["athletes"][0]["is_postseason"])
        self.assertEqual(parsed["results"][0]["result"], "16:25")

    def test_template_layout_reads_metadata_after_title_and_coaches_rows(self):
        rows = [
            ["HHS Cross Country Data 2026"],
            [None, "< Boys Coaches (Separated by commas, head coach first)"],
            [None, None, "Race Type >", "4k", "5k"],
            [None, None, "Location >", "Brownsburg", "Amp"],
            [None, None, "Date >", date(2026, 8, 22), date(2026, 8, 25)],
            [None, None, "Meet Notes >", "Check back soon", "Times are rounded"],
            [None, None, "Boys Place >", None, "1st"],
            [None, None, "Girls Place >", "3rd", "1st"],
            ["Name", "Grade", "Team", "Brownsburg 4k", "Champ at the Amp"],
            ["Runner Boy", 12, "B", None, "16:19.00"],
            ["Runner Girl", 11, "G", None, "18:10.00"],
        ]

        parsed = parse_year_sheet(rows, 2026, set())

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["layout"]["meet_type_row"], 2)
        self.assertEqual(parsed["layout"]["location_row"], 3)
        self.assertEqual(parsed["layout"]["date_row"], 4)
        self.assertEqual(parsed["layout"]["notes_row"], 5)
        self.assertEqual(parsed["layout"]["boys_place_row"], 6)
        self.assertEqual(parsed["layout"]["girls_place_row"], 7)
        self.assertEqual(parsed["meets"][1]["type"], "5k")
        self.assertEqual(parsed["meets"][1]["location"], "Amp")
        self.assertTrue(parsed["results"][0]["is_5k"])
        self.assertEqual(parsed["meets"][1]["girls_place"], "1st")

    def test_current_layout_reads_team_and_gender_places(self):
        rows = [
            ["HHS Cross Country Data 2026"],
            ["", "", "Race Type >", "5K"],
            ["", "", "Location >", "Town"],
            ["", "", "Date >", "2026-10-01"],
            ["", "", "Meet Notes >", "Notes"],
            ["", "", "Boys Place >", "2nd"],
            ["", "", "Girls Place >", "1st"],
            ["Name", "Grade", "Team", "Meet One"],
            ["Runner Boy", 12, "B", "16:25.347"],
            ["Runner Girl", 11, "G", "18:10"],
        ]
        parsed = parse_year_sheet(rows, 2026, set())
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["athletes"][0]["team"], "B")
        self.assertEqual(parsed["athletes"][1]["team"], "G")
        self.assertEqual(parsed["meets"][0]["boys_place"], "2nd")
        self.assertEqual(parsed["meets"][0]["girls_place"], "1st")
        self.assertEqual(parsed["results"][0]["team"], "B")
        self.assertEqual(parsed["results"][0]["result"], "16:25.347")

    def test_non_time_results_are_not_exposed_or_guessed_as_times(self):
        rows = [
            [],
            ["Name", "Grade", "", "DNR Meet", "Sick Meet", "Question Meet", "Blank Meet", "Timed Meet"],
            [],
            [],
            [],
            [],
            [],
            ["Runner", "Senior", "", "dnr", "sick", "?", None, "16:25"],
        ]
        parsed = parse_year_sheet(rows, 2026, set())
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(len(parsed["athletes"]), 1)
        self.assertEqual(parsed["athletes"][0]["grade"], "Senior")
        self.assertEqual(len(parsed["results"]), 1)
        self.assertEqual(parsed["results"][0]["meet"], "Timed Meet")
        self.assertEqual(parsed["results"][0]["result"], "16:25")
        self.assertEqual(parsed["results"][0]["seconds"], Decimal(985))
        self.assertEqual(parsed["athletes"][0]["results"], parsed["results"])

    def test_unformatted_numeric_result_is_not_exposed(self):
        rows = [
            [],
            ["Name", "Grade", "", "Meet"],
            [],
            [],
            [],
            [],
            [],
            ["Runner", "Senior", "", 0.0114],
        ]
        parsed = parse_year_sheet(rows, 2026, set())
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["results"], [])
        self.assertEqual(parsed["athletes"][0]["results"], [])

    def test_workbook_parser_reads_values_and_bold_style(self):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "2026"
        worksheet.append(["", "", "", ""])
        worksheet.append(["Name", "Grade", "", "Meet One"])
        worksheet.append(["Meet Type", "", "", "Invitational"])
        worksheet.append(["Location", "", "", "Town"])
        worksheet.append(["Date", "", "", date(2026, 10, 1)])
        worksheet.append(["Notes", "", "", ""])
        worksheet.append(["Team Place", "", "", 2])
        worksheet.append(["Runner One", 12, "", time(0, 16, 25)])
        worksheet.append(["Runner Two", 11, "", time(0, 17, 0)])
        worksheet["A8"].font = openpyxl.styles.Font(bold=True)
        worksheet["D8"].font = openpyxl.styles.Font(bold=True)

        outdated = workbook.create_sheet("2025")
        outdated.append(["Old", "Format"])

        stream = BytesIO()
        workbook.save(stream)
        workbook.close()

        parsed_years = parse_workbook_years(stream.getvalue())
        self.assertEqual(list(parsed_years["years"]), [2026])
        self.assertEqual(len(parsed_years["issues"]), 1)
        self.assertIn("2025", parsed_years["issues"][0])
        result = parsed_years["years"][2026]["results"][0]
        self.assertEqual(result["raw_result"], time(0, 16, 25))
        self.assertEqual(result["seconds"], Decimal(985))
        self.assertEqual(result["result"], "16:25")
        self.assertTrue(result["is_varsity"])
        self.assertTrue(parsed_years["years"][2026]["athletes"][0]["is_postseason"])
        self.assertFalse(parsed_years["years"][2026]["athletes"][1]["is_postseason"])

    def test_postseason_roster_ranks_pr_and_compares_previous_season(self):
        previous_rows = [
            [],
            ["Name", "Grade", "", "5K Invitational"],
            ["Meet Type", "", "", "5K"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2025, 10, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner One", 11, "", "16:50"],
            ["Runner Two", 11, "", "16:45"],
            ["Runner Three", 11, "", "16:40"],
        ]
        current_rows = [
            [],
            ["Name", "Grade", "", "5K Invitational", "5K Championship"],
            ["Meet Type", "", "", "5K", "5K"],
            ["Location", "", "", "Town", "City"],
            ["Date", "", "", date(2026, 9, 1), date(2026, 10, 1)],
            ["Notes", "", "", "", ""],
            ["Team Place", "", "", 2, 1],
            ["Runner One", 12, "", "16:35", "16:40"],
            ["Runner Two", 12, "", "16:20", "16:29"],
            ["Runner Three", 12, "", "16:50", "16:55"],
            ["Not Postseason", 12, "", "15:00", ""],
        ]
        previous = parse_year_sheet(previous_rows, 2025, {(7, 0), (8, 0), (9, 0)})
        current = parse_year_sheet(current_rows, 2026, {(7, 0), (8, 0), (9, 0)})
        self.assertIsNotNone(previous)
        self.assertIsNotNone(current)
        assert previous is not None and current is not None

        roster = build_postseason_roster({2025: previous, 2026: current}, 2026)
        self.assertEqual(len(roster), 3)
        all_runners = build_postseason_roster(
            {2025: previous, 2026: current},
            2026,
            postseason_only=False,
        )
        self.assertEqual(
            {athlete["Athlete"] for athlete in all_runners},
            {"Runner One", "Runner Two", "Runner Three", "Not Postseason"},
        )
        self.assertEqual(roster[0]["Rank"], 1)
        self.assertEqual(roster[0]["Athlete"], "Runner Two")
        self.assertEqual(roster[0]["PR"], "16:20")
        self.assertEqual(roster[0]["Improvement"], "-0:00:25 (-2.5%)")
        self.assertEqual(roster[1]["Rank"], 2)
        self.assertEqual(roster[1]["Athlete"], "Runner One")
        self.assertEqual(roster[1]["Grade"], "12")
        self.assertEqual(roster[1]["PR"], "16:35")
        self.assertEqual(roster[1]["Meet"], "5K Invitational")
        self.assertEqual(roster[1]["Improvement"], "-0:00:15 (-1.5%)")
        self.assertEqual(roster[2]["Athlete"], "Runner Three")
        self.assertEqual(roster[2]["Rank"], 3)
        self.assertEqual(roster[2]["Improvement"], "+0:00:10 (+1.0%)")

    def test_improvement_formats_elapsed_time_and_year_over_year_percent(self):
        previous_rows = [
            [],
            ["Name", "Grade", "", "5K"],
            ["Meet Type", "", "", "5K"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2025, 10, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner", 11, "", "16:25.500"],
        ]
        current_rows = [
            [],
            ["Name", "Grade", "", "5K"],
            ["Meet Type", "", "", "5K"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2026, 10, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner", 12, "", "16:25.250"],
        ]
        previous = parse_year_sheet(previous_rows, 2025, {(7, 0)})
        current = parse_year_sheet(current_rows, 2026, {(7, 0)})
        self.assertIsNotNone(previous)
        self.assertIsNotNone(current)
        assert previous is not None and current is not None

        roster = build_postseason_roster({2025: previous, 2026: current}, 2026)
        self.assertEqual(roster[0]["Improvement"], "-0:00:00.25 (0.0%)")
        self.assertEqual(roster[0]["PR"], "16:25.25")

        unchanged_season = parse_year_sheet(previous_rows, 2026, {(7, 0)})
        self.assertIsNotNone(unchanged_season)
        assert unchanged_season is not None
        unchanged = build_postseason_roster(
            {2025: previous, 2026: unchanged_season},
            2026,
        )
        self.assertEqual(unchanged[0]["Improvement"], "0:00:00 (0.0%)")

    def test_athlete_5k_chart_filters_meet_type_and_sorts_by_date(self):
        rows = [
            [],
            ["Name", "Grade", "", "Late 5k", "Early 5K", "Early non-5K", "No time 5k"],
            ["Meet Type", "", "", "Invitational 5K", "5k", "3K", "5K"],
            ["Location", "", "", "Town", "Town", "Town", "Town"],
            ["Date", "", "", date(2026, 10, 10), date(2026, 9, 10), date(2026, 9, 1), date(2026, 9, 5)],
            ["Notes", "", "", "", "", "", ""],
            ["Team Place", "", "", "", "", "", ""],
            ["Runner", 12, "", "16:30", "16:40", "10:00", "dnf"],
        ]
        parsed = parse_year_sheet(rows, 2026, set())
        self.assertIsNotNone(parsed)
        assert parsed is not None

        chart_results = build_athlete_5k_chart_data(parsed["results"])
        self.assertEqual(
            [result["meet"] for result in chart_results],
            ["Early 5K", "Late 5k"],
        )
        self.assertEqual([result["year"] for result in chart_results], ["2026", "2026"])
        self.assertEqual(
            [result["time"] for result in chart_results],
            ["16:40", "16:30"],
        )
        self.assertEqual(
            [result["marker"] for result in chart_results],
            ["square", "star"],
        )

    def test_athlete_5k_chart_uses_parser_5k_flag(self):
        chart_data = build_athlete_5k_chart_data(
            [
                {
                    "name": "Runner",
                    "year": 2026,
                    "meet": "Girls Invite",
                    "type": "Cross Country",
                    "is_5k": True,
                    "raw_date": date(2026, 9, 1),
                    "date": "September 1",
                    "result": "19:10",
                    "seconds": Decimal(1150),
                }
            ]
        )
        self.assertEqual(len(chart_data), 1)
        self.assertEqual(chart_data[0]["time"], "19:10")

    def test_postseason_chart_includes_career_pr_markers_for_roster_athletes(self):
        previous_rows = [
            [],
            ["Name", "Grade", "", "Previous 5K"],
            ["Meet Type", "", "", "5K"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2025, 10, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner One", 11, "", "17:00"],
        ]
        current_rows = [
            [],
            ["Name", "Grade", "", "Early 5K", "Late 5K"],
            ["Meet Type", "", "", "5K", "5K"],
            ["Location", "", "", "Town", "Town"],
            ["Date", "", "", date(2026, 9, 1), date(2026, 10, 1)],
            ["Notes", "", "", "", ""],
            ["Team Place", "", "", 1, 1],
            ["Runner One", 12, "", "16:30", "16:45"],
            ["Runner Two", 12, "", "16:50", ""],
            ["Not Postseason", 12, "", "15:00", ""],
        ]
        previous = parse_year_sheet(previous_rows, 2025, {(7, 0)})
        current = parse_year_sheet(current_rows, 2026, {(7, 0), (8, 0)})
        self.assertIsNotNone(previous)
        self.assertIsNotNone(current)
        assert previous is not None and current is not None

        chart_rows = build_postseason_season_chart_data(
            {2025: previous, 2026: current},
            2026,
        )
        self.assertEqual(
            [(row["athlete"], row["meet"], row["marker"]) for row in chart_rows],
            [
                ("Runner One", "Early 5K", "star"),
                ("Runner Two", "Early 5K", "star"),
                ("Runner One", "Late 5K", "circle"),
            ],
        )

    def test_race_totals_count_results_sum_duration_and_use_earliest_result_year(self):
        earlier_rows = [
            [],
            ["Name", "Grade", "", "Early Meet"],
            ["Meet Type", "", "", "5K"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2023, 9, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner One", 10, "", "16:00"],
        ]
        later_rows = [
            [],
            ["Name", "Grade", "", "Later Meet"],
            ["Meet Type", "", "", "Invitational"],
            ["Location", "", "", "Town"],
            ["Date", "", "", date(2024, 9, 1)],
            ["Notes", "", "", ""],
            ["Team Place", "", "", 1],
            ["Runner One", 11, "", "17:00"],
            ["Runner Two", 10, "", "18:00"],
        ]
        earlier = parse_year_sheet(earlier_rows, 2023, set())
        later = parse_year_sheet(later_rows, 2024, set())
        self.assertIsNotNone(earlier)
        self.assertIsNotNone(later)
        assert earlier is not None and later is not None

        totals = build_race_totals({2023: earlier, 2024: later})
        self.assertEqual(totals, {
            "race_count": 3,
            "hours_raced": Decimal("0.9"),
            "first_year": 2023,
        })

    def test_race_totals_since_year_ignores_earlier_seasons_without_results(self):
        empty_earlier_season = {
            "meets": [{"raw_date": date(2020, 9, 1)}],
            "results": [],
        }
        first_season_with_results = {
            "meets": [{"raw_date": date(2023, 9, 1)}],
            "results": [{"year": 2023, "seconds": Decimal(960)}],
        }
        later_season = {
            "meets": [{"raw_date": date(2024, 9, 1)}],
            "results": [{"year": 2024, "seconds": Decimal(1020)}],
        }

        totals = build_race_totals(
            {
                2020: empty_earlier_season,
                2023: first_season_with_results,
                2024: later_season,
            }
        )

        self.assertEqual(totals, {
            "race_count": 2,
            "hours_raced": Decimal("0.6"),
            "first_year": 2023,
        })


if __name__ == "__main__":
    unittest.main()
