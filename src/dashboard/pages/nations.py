"""Nations: req d + E8 participation by country with drill-down, E9 national outcomes, choropleth."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, features, filters, queries, ui
from lib import format as fmt

state = st.session_state

riders_by_country = queries.participation("rider")
teams_by_country = queries.participation("team")
names = dict(zip(riders_by_country["iso"], riders_by_country["country_name"]))
if state.get("w_country") not in names:
    state.w_country = riders_by_country.iloc[0]["iso"]

ui.header(["Nations", names[state.w_country]], "Country participation")
f = filters.bar()

# The database's country codes follow the race (IOC style). The world map needs true ISO-3 codes.
MAP_CODES = {"DEN": "DNK", "GER": "DEU", "LAT": "LVA", "NED": "NLD", "POR": "PRT", "SLO": "SVN", "SUI": "CHE"}

k = queries.country_kpis()
ui.kpi_tiles([
    ("Rider nations", int(k.rider_nations), "distinct riders.country"),
    ("Team nations", int(k.team_nations), "distinct teams.country"),
    ("Countries in DB", int(k.countries_in_db), f"{int(k.countries_without_riders)} with a team but no rider"),
    ("Racing abroad", f"{k.riders_abroad / k.riders * 100:.1f}%", f"{int(k.riders_abroad)} of {int(k.riders)} · rider nation ≠ team nation"),
])


def country_table(data, label):
    """Bars inside a table; the country chosen in the drill-down below stays highlighted."""
    view = pd.DataFrame({"Code": data["iso"], "Country": data["country_name"], label: data["n"]}).reset_index(drop=True)
    styler = view.style.apply(lambda c: ["background-color:#EEF3FA;font-weight:700" if code == state.w_country else "" for code in view["Code"]], subset=["Code", "Country"])
    ui.table(view, styler=styler, height=40 + 35 * len(view), column_config={
        label: st.column_config.ProgressColumn(label, format="%d", min_value=0, max_value=int(data["n"].max()), color="#2E5FA8"),
    })


left, right = st.columns(2)
with left:
    with ui.card("riders_country", "Riders per country", tag="Req. d · E8", sub="By rider nationality (riders.country) · choose a country in the drill-down below"):
        country_table(riders_by_country, "Riders")
with right:
    with ui.card("teams_country", "Teams per country", tag="Req. d · E8", sub="By team registration (teams.country) · independent of rider nationality"):
        country_table(teams_by_country, "Teams")
        ui.note("BRN, ISR and UAE register a team but have no rider in the race.")
    with ui.card("map", "Riders on the map", tag="Req. d", sub="Riders per nation"):
        st.plotly_chart(charts.choropleth(
            [MAP_CODES.get(iso, iso) for iso in riders_by_country["iso"]], list(riders_by_country["n"]), list(riders_by_country["country_name"]),
        ), width="stretch", config={"displayModeBar": False}, key="map_chart")

# Without E9, the E8 drill-down takes the full row
left, right = st.columns(2) if features.on("E9") else (st.container(), None)
# ---------- E8 country drill-down ----------
with left:
    code = state.w_country
    all_riders = queries.riders()
    squad = all_riders[all_riders["rider_country"] == code].assign(abroad=lambda d: d["team_country"] != code) \
        .sort_values(["abroad", "rider_name"], ascending=[False, True])
    n_teams = teams_by_country.loc[teams_by_country["iso"] == code, "n"].sum()
    with ui.card("country", f"{len(squad)} rider{'s' if len(squad) != 1 else ''} · {n_teams} team{'s' if n_teams != 1 else ''} registered in {escape(names[code])}",
                 tag="E8", drill="Drill-down · country",
                 sub=f"{int(squad['abroad'].sum())} of them race for teams registered abroad (team country highlighted)"):
        st.selectbox("Choose a country", riders_by_country["iso"].tolist(), key="w_country",
                     format_func=lambda iso: f"{names[iso]} ({iso}) · {riders_by_country.set_index('iso').loc[iso, 'n']} riders")
        view = pd.DataFrame({"Rider": squad["rider_name"], "Team": squad["team"], "Team country": squad["team_country"]})
        styler = view.style.map(lambda c: "" if c == code else "color:#B4541C;font-weight:700", subset=["Team country"])
        ui.table(view, styler=styler, height=min(38 + 35 * len(view), 420))

# ---------- E9 national outcomes ----------
if right is not None:
    with right:
        with ui.card("outcomes", "National outcomes", tag="E9", sub="Best GC finish, stage wins and podiums by rider nationality over the selected stages · click a value to see what is behind it"):
            outcomes = queries.national_outcomes(f).reset_index(drop=True)
            view = pd.DataFrame({
                "Nation": outcomes["iso"], "Country": outcomes["country_name"], "Riders": outcomes["riders"],
                "Best GC": outcomes["best_gc"].map(fmt.rank_or_dash), "Stage wins": outcomes["stage_wins"], "Podiums": outcomes["podiums"],
            })
            event = ui.table(view, key="t_outcomes", right=["Best GC"], select="cell", height=min(38 + 35 * len(view), 420))
            cell = ui.new_cell(event, "t_outcomes")
            if cell is not None and cell[1] in ("Best GC", "Stage wins", "Podiums"):
                state.w_outcome = (outcomes.iloc[int(cell[0])].iso, cell[1])
            chosen = state.get("w_outcome")
            if not chosen:
                ui.note("Click a Best GC, Stage wins or Podiums value.")
            else:
                iso, column = chosen
                row = outcomes[outcomes["iso"] == iso].iloc[0]
                if column == "Best GC":
                    if pd.isna(row.best_gc):
                        ui.html(f'<div class="callout"><b>{iso}:</b> no rider finished the selection.</div>')
                    else:
                        ui.html(f'<div class="callout"><b>{iso} · Best GC:</b> {escape(row.best_gc_rider)}, {fmt.ordinal(row.best_gc)}</div>')
                        if st.button(f"Open {row.best_gc_rider} →", key="open_best"):
                            ui.goto("riders", w_rider=int(row.best_gc_bib))
                else:
                    results = queries.national_results(f, iso, 1 if column == "Stage wins" else 3)
                    ui.html(f'<div class="callout"><b>{iso} · {column} ({len(results)})</b></div>')
                    if not results.empty:
                        detail = pd.DataFrame({"Stage": "S" + results["stage_no"].astype(str) + " · " + results["route"], "Rider": results["rider_name"], "Rank": results["rank"]})
                        ui.table(detail, height=min(38 + 35 * len(detail), 280))
