"""Smoke test: every page must draw without an exception under ordinary and edge-case filters."""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parent.parent / "src" / "dashboard"
sys.path.insert(0, str(DASHBOARD))

PAGES = ["overview", "gc", "stages", "time_trials", "riders", "teams", "nations", "about"]
SCENARIOS = {
    "whole race": {},
    "mountain only": {"w_types": ["Mountain"]},
    "itt only": {"w_types": ["ITT"]},
    "flat only": {"w_types": ["Flat"]},
    "single stage": {"w_from": 5, "w_to": 5},
    "first stages": {"w_from": 1, "w_to": 3},
    "one-rider nation": {"w_nation": "RUS"},
    "one team": {"w_team": "LOTTO"},
    "low young cutoff": {"w_cutoff": 18},
    "replay without bonuses": {"w_cf_remove": ["Bonuses"]},
    "replay without both": {"w_cf_remove": ["Bonuses", "Penalties"]},
    "exited riders plotted": {"w_story": [1, 106], "w_gc_exited": [106], "w_focus": 106},
    "gc after early stage": {"w_after": 3},
    "top-10 movement appears": {"w_from": 8},
    "all riders tables": {"w_par_all": True, "w_gc_all": True},
    "exited rider": {"w_rider": 64},
    "no stage matches": {"w_from": 1, "w_to": 2, "w_types": ["ITT"]},
}


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("page", PAGES)
def test_page_draws(page, scenario):
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    for key, value in SCENARIOS[scenario].items():
        app.session_state[key] = value
    app.switch_page(f"pages/{page}.py")
    app.run()
    assert not app.exception, [e.value for e in app.exception]


@pytest.mark.parametrize("page, widget", [("gc", "w_after"), ("riders", "w_rider"), ("nations", "w_country")])
def test_navigation_reaches_the_page(page, widget):
    """Guards the smoke test above: each run must really draw the requested page, not the default one."""
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    app.switch_page(f"pages/{page}.py")
    app.run()
    assert app.selectbox(key=widget) is not None


def test_dates_format_without_platform_specific_codes():
    """Windows strftime rejects glibc codes such as "%-d", which crashed every page there."""
    from datetime import date

    from lib import format as fmt

    day = date(2025, 7, 5)
    assert fmt.long_date(day) == "Sat 5 Jul 2025"
    assert fmt.medium_date(day) == "5 Jul 2025"
    assert fmt.short_date(day) == "5 Jul"
    offenders = [path.name for path in DASHBOARD.rglob("*.py") if re.search(r"%[-#][a-zA-Z]", path.read_text(encoding="utf-8"))]
    assert not offenders
