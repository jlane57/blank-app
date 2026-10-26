import unittest

from team_views import available_team_selections, filter_results


class TeamViewTests(unittest.TestCase):
    def test_filter_results_keeps_boys_and_girls_together_without_split(self):
        results = [
            {"team": "B", "is_varsity": None, "name": "Boy"},
            {"team": "G", "is_varsity": None, "name": "Girl"},
        ]
        self.assertEqual(
            [row["name"] for row in filter_results(results, "B")],
            ["Boy"],
        )

    def test_available_team_selections_use_gender_tabs_without_bold_times(self):
        results = [
            {"team": "B", "is_varsity": None},
            {"team": "G", "is_varsity": None},
        ]
        self.assertEqual(set(available_team_selections(results)), {"B", "G"})

    def test_available_team_selections_use_division_tabs_with_bold_times(self):
        results = [
            {"team": "B", "is_varsity": True},
            {"team": "G", "is_varsity": False},
        ]
        self.assertEqual(
            set(available_team_selections(results)),
            {"B_VARSITY", "B_JV", "G_VARSITY", "G_JV"},
        )

    def test_filter_results_separates_team_and_division(self):
        results = [
            {"team": "B", "is_varsity": True, "name": "Boy Varsity"},
            {"team": "B", "is_varsity": False, "name": "Boy JV"},
            {"team": "G", "is_varsity": True, "name": "Girl Varsity"},
            {"team": "G", "is_varsity": False, "name": "Girl JV"},
        ]
        self.assertEqual(
            [row["name"] for row in filter_results(results, "G_JV")],
            ["Girl JV"],
        )


if __name__ == "__main__":
    unittest.main()
