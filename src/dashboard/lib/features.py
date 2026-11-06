"""Which optional OLAP narratives the dashboard shows.

The group chose to present E1, E2, E4, E5, E7, E8, E10, E11 and E14, plus the Best team table for
requirement c. The narratives below set to False are fully built but hidden; set one to True to bring it
back. Narratives not listed are always shown.
"""
EXTRAS = {
    "Best team": True,  # Teams: Best team classification table, kept for requirement c (team cumulative times)
    "E3": False,   # Teams: "who carried the time" drill-down from the Best team table
    "E6": False,   # Riders: Speed by terrain and biggest gainers
    "E9": False,   # Nations: National outcomes
    "E12": False,  # Riders: Consistency near the front
    "E13": False,  # Teams: Squad depth and roster drill-down
    "E15": False,  # Stages: The long day and longest-stage spotlight
}


def on(narrative):
    return EXTRAS.get(narrative, True)
