import unittest

from team_views import filter_results


class TeamViewTests(unittest.TestCase):
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
