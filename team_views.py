import random


TEAM_OPTIONS = {
    "B": ("B", None, "Boys"),
    "G": ("G", None, "Girls"),
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
        and (varsity is None or result.get("is_varsity") is varsity)
    ]


def filter_athletes(athletes, team=None):
    if team is None:
        return list(athletes)
    return [athlete for athlete in athletes if athlete.get("team", "").upper() == team]


def available_team_selections(results):
    """Return the result tabs to show for a meet.

    Each gender is handled on its own: if at least one of its athletes is bold
    (varsity) in the meet, it gets Varsity and JV tabs. If none are bold there
    is no way to tell varsity from JV, so it gets a single tab ("Boys" or
    "Girls") listing everyone instead of putting every entry under JV.
    """
    genders = ["B", "G"]
    if random.SystemRandom().choice((True, False)):
        genders.reverse()

    selections = []
    for gender in genders:
        has_varsity = any(
            str(result.get("team", "")).upper() == gender
            and result.get("is_varsity") is True
            for result in results
        )
        if has_varsity:
            selections.extend((f"{gender}_VARSITY", f"{gender}_JV"))
        else:
            selections.append(gender)
    return selections


def randomized_team_order():
    if random.SystemRandom().choice((True, False)):
        return ["B_VARSITY", "B_JV", "G_VARSITY", "G_JV"]
    return ["G_VARSITY", "G_JV", "B_VARSITY", "B_JV"]
