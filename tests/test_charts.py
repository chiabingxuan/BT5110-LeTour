"""Checks for the race-themed charts: the race to the line, the route as a road and the stage podium.
The inputs are small hand-made frames shaped like the query results; they test the drawing logic only."""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dashboard"))
from lib import charts  # noqa: E402
from lib.team import MY, Context  # noqa: E402

CTX = Context("A", ("B",))


def test_race_to_line_has_one_frame_per_stage_and_rings_the_leader():
    gc = pd.DataFrame({
        "rider_bib": [1, 2, 3, 1, 2, 3], "rider_name": ["Ann One", "Bo Two", "Cy Three"] * 2,
        "seq": [1, 1, 1, 2, 2, 2], "gc_rank": [1, 2, 3, 2, 1, 3], "gap": [0, 30, 90, 20, 0, 300],
    })
    stages = pd.DataFrame({"seq": [1, 2], "stage_no": [1, 2], "route": ["X → Y", "Y → Z"]})
    fig = charts.race_to_line(gc, stages, CTX, {1: "A", 2: "B", 3: "C"}, labelled={1})
    assert [f.name for f in fig.frames] == ["1", "2"]
    last = fig.frames[-1].data[0]
    # After stage 2 rider 2 leads: named and ringed in yellow, and the axis reaches past the last rider
    assert list(last.text) == ["Two", "One", ""]
    assert last.marker.line.color[0] == "#F5C400"
    assert fig.frames[-1].layout.xaxis.range[0] > 300 / 60


def test_route_road_merges_labels_of_back_to_back_wins():
    stages = pd.DataFrame({
        "stage_no": [1, 2, 3], "date": [date(2025, 7, 5), date(2025, 7, 6), date(2025, 7, 8)],
        "dist_km": [100.0, 150.0, 120.0], "type": ["flat", "mountain", "hilly"], "type_label": ["Flat", "Mountain", "Hilly"],
        "route": ["a → b", "b → c", "c → d"], "winner_name": ["Ann One", "Ann One", "Bo Two"],
        "start_location": ["a", "b", "c"], "end_location": ["b", "c", "d"],
    })
    fig = charts.route_road(stages, {1, 2, 3}, {1: "A", 2: "A", 3: "B"}, CTX)
    stars = fig.data[-1]
    assert list(stars.text) == ["One ×2", "", ""]
    assert stars.marker.color[0] == MY
    # The two-day gap before stage 3 is marked as a rest day
    assert any(a.text == "rest" for a in fig.layout.annotations)


def test_podium_puts_the_winner_on_the_middle_and_tallest_block():
    rows = pd.DataFrame({"rank": [1, 2, 3], "rider_name": ["Ann One", "Bo Two", "Cy Three"], "team": ["A", "B", "C"], "gap": [0, 5, 12]})
    fig = charts.podium(rows, CTX)
    blocks = [s for s in fig.layout.shapes if s.type == "rect"]
    winner = max(blocks, key=lambda s: s.y1)
    assert (winner.x0 + winner.x1) / 2 == 1 and winner.fillcolor == MY
