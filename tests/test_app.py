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
    "exited riders plotted": {"w_story": [1, 106], "w_gc_exited": [106], "w_focus": 106, "w_gc_compare": [1]},
    "gc after early stage": {"w_after": 3},
    "top-10 movement appears": {"w_from": 7},
    "all riders tables": {"w_par_all": True, "w_gc_all": True},
    "points and kom shown": {"w_par_derived": True},
    "linear rank axis": {"w_rank_scale": "Linear", "w_story": [1, 106], "w_gc_exited": [106]},
    "exited rider": {"w_rider": 64},
    "no stage matches": {"w_from": 1, "w_to": 2, "w_types": ["ITT"]},
    "small team, no rivals": {"w_my_team": "LOTTO", "w_rivals": []},
    "leading team as my team": {"w_my_team": "TEAM VISMA | LEASE A BIKE"},
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


def test_filter_banner_does_not_change_when_a_filter_changes():
    """A changed expander title or flag makes Streamlit redraw it closed, so clicking a filter shut the banner."""

    def banner(state):
        app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
        for key, value in state.items():
            app.session_state[key] = value
        app.run()
        return app.expander[0].label, app.expander[0].proto.expanded

    assert banner({}) == banner({"w_types": ["Flat"], "w_from": 3, "w_to": 9})


def test_app_rebuilds_outdated_views_on_start():
    """Teammates pulled new code without re-running init_db, and the GC page crashed on a missing column.
    The app must notice the SQL changed and rebuild the views itself."""
    import os

    import psycopg2
    from dotenv import load_dotenv

    sys.path.insert(0, str(DASHBOARD.parent))
    import init_db

    load_dotenv(DASHBOARD.parents[1] / ".env")
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    )
    with connection, connection.cursor() as cursor:
        # Simulate a database built from an older version: no combined replay columns, old fingerprint
        cursor.execute("DROP FUNCTION fn_gc_final(int, int, text[], int) CASCADE")
        cursor.execute(f"COMMENT ON {init_db.FINGERPRINT_TARGET} IS 'letour-views:outdated'")
        assert init_db.refresh_views_if_stale(cursor) is True
        assert init_db.refresh_views_if_stale(cursor) is False
        cursor.execute("SELECT no_both_rank FROM fn_gc_final() LIMIT 1")
        assert init_db.installed_fingerprint(cursor) == init_db.views_fingerprint()
    connection.close()


@pytest.fixture
def extras_on():
    """Switches every hidden narrative back on for one test, then restores the settings."""
    from lib import features

    saved = dict(features.EXTRAS)
    features.EXTRAS.update({name: True for name in features.EXTRAS})
    yield
    features.EXTRAS.clear()
    features.EXTRAS.update(saved)


@pytest.mark.parametrize("page", PAGES)
def test_hidden_narratives_still_draw_when_switched_on(page, extras_on):
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    app.switch_page(f"pages/{page}.py")
    app.run()
    assert not app.exception, [e.value for e in app.exception]


def _has_widget(app, kind, key):
    try:
        getattr(app, kind)(key=key)
        return True
    except KeyError:
        return False


@pytest.mark.parametrize("switched_on", [False, True])
def test_switches_hide_and_show_narratives(switched_on, request):
    if switched_on:
        request.getfixturevalue("extras_on")
    # E6 has a widget of its own; E3's drill-down is the only thing that picks a team to drill into
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    app.switch_page("pages/riders.py")
    app.run()
    assert _has_widget(app, "segmented_control", "w_grain") is switched_on
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    app.switch_page("pages/teams.py")
    app.run()
    assert ("w_team_sel" in app.session_state) is switched_on


def test_best_team_table_shows_for_requirement_c():
    """The Best team table stays on even though the rest of E3 is hidden."""
    app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30)
    app.switch_page("pages/teams.py")
    app.run()
    assert not app.exception
    assert _has_widget(app, "toggle", "w_bt_all")
