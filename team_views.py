import random


TEAM_OPTIONS = {
    "B_VARSITY": ("B", True, "Boys Varsity"),
    "B_JV": ("B", False, "Boys JV"),
    "G_VARSITY": ("G", True, "Girls Varsity"),
    "G_JV": ("G", False, "Girls JV"),
}


def filter_results(results, selection):
    team, varsity, _ = TEAM_OPTIONS[selection]
    return [
        result
        for result in results
        if result.get("team", "").upper() == team
        and result.get("is_varsity") is varsity
    ]


def filter_athletes(athletes, team=None):
    if team is None:
        return list(athletes)
    return [athlete for athlete in athletes if athlete.get("team", "").upper() == team]


def randomized_team_order():
    if random.SystemRandom().choice((True, False)):
        return ["B_VARSITY", "B_JV", "G_VARSITY", "G_JV"]
    return ["G_VARSITY", "G_JV", "B_VARSITY", "B_JV"]
