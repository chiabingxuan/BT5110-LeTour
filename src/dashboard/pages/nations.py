"""Chapter 5, Scouting: req d + E8 where the riders come from (map, riders and teams per country, country
drill-down), young prospects outside our team, E9 national outcomes (hidden)."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, features, filters, queries, team, ui
from lib import format as fmt

state = st.session_state

riders_by_country = queries.participation("rider")
teams_by_country = queries.participation("team")
names = dict(zip(riders_by_country["iso"], riders_by_country["country_name"]))
if state.get("w_country") not in names:
    state.w_country = riders_by_country.iloc[0]["iso"]

ctx = team.context()
ui.header(["5 · Scouting", names[state.w_country]], "Who should we scout?")
f = filters.bar(young=True)

# The database's country codes follow the race (IOC style). The world map needs true ISO-3 codes.
MAP_CODES = {"DEN": "DNK", "GER": "DEU", "LAT": "LVA", "NED": "NLD", "POR": "PRT", "SLO": "SVN", "SUI": "CHE"}

k = queries.country_kpis()
ui.kpi_tiles([
    ("Rider nations", int(k.rider_nations), "distinct riders.country"),
    ("Team nations", int(k.team_nations), "distinct teams.country"),
    ("Countries in DB", int(k.countries_in_db), f"{int(k.countries_without_riders)} with a team but no rider"),
    ("Racing abroad", f"{k.riders_abroad / k.riders * 100:.1f}%", f"{int(k.riders_abroad)} of {int(k.riders)} · rider nation ≠ team nation"),
])


all_riders = queries.riders()
our_nations = set(all_riders.loc[all_riders["team"] == ctx.my, "rider_country"])
our_country = all_riders.loc[all_riders["team"] == ctx.my, "team_country"].iloc[0] if ctx.my in set(all_riders["team"]) else None


def country_table(data, label):
    """Full table behind Show data; the country chosen in the drill-down stays highlighted."""
    view = pd.DataFrame({"Code": data["iso"], "Country": data["country_name"], label: data["n"]}).reset_index(drop=True)
    styler = view.style.apply(lambda c: ["background-color:#EEF3FA;font-weight:700" if code == state.w_country else "" for code in view["Code"]], subset=["Code", "Country"])
    ui.table(view, styler=styler, height=40 + 35 * len(view), column_config={
        label: st.column_config.ProgressColumn(label, format="%d", min_value=0, max_value=int(data["n"].max()), color="#2E5FA8"),
    })


# ---------- Req d + E8: where the riders come from ----------
with ui.card("map", "Where the riders come from", tag="Req. d · E8", sub="Riders per nation (rider nationality) · darker = more riders"):
    top_nation = riders_by_country.iloc[0]
    ui.takeaway(f"{escape(top_nation.country_name)} supplies the most riders ({top_nation.n}) of {len(riders_by_country)} nations; "
                f"our {len(all_riders[all_riders['team'] == ctx.my])} riders come from {len(our_nations)} of them.")
    st.plotly_chart(charts.choropleth(
        [MAP_CODES.get(iso, iso) for iso in riders_by_country["iso"]], list(riders_by_country["n"]), list(riders_by_country["country_name"]),
    ), width="stretch", config={"displayModeBar": False, "scrollZoom": False}, key="map_chart")

left, right = st.columns(2)
with left:
    with ui.card("riders_country", "Riders per country", tag="Req. d · E8", sub="By rider nationality (riders.country) · top 15 · our riders' nations in our colour"):
        top15 = riders_by_country.head(15)
        st.plotly_chart(charts.h_bars([f"{n} ({c})" for n, c in zip(top15["country_name"], top15["iso"])], list(top15["n"]),
                                      [team.MY if iso in our_nations else "#9DB9E0" for iso in top15["iso"]]),
                        width="stretch", config={"displayModeBar": False}, key="riders_country_chart")
        with st.expander(f"Show data: all {len(riders_by_country)} nations"):
            country_table(riders_by_country, "Riders")
with right:
    with ui.card("teams_country", "Teams per country", tag="Req. d · E8", sub="By team registration (teams.country) · independent of rider nationality · our team's country in our colour"):
        st.plotly_chart(charts.h_bars([f"{n} ({c})" for n, c in zip(teams_by_country["country_name"], teams_by_country["iso"])], list(teams_by_country["n"]),
                                      [team.MY if iso == our_country else "#9DB9E0" for iso in teams_by_country["iso"]]),
                        width="stretch", config={"displayModeBar": False}, key="teams_country_chart")
        ui.note("BRN, ISR and UAE register a team but have no rider in the race.")
        with st.expander("Show data"):
            country_table(teams_by_country, "Teams")

# ---------- Young prospects outside our team ----------
state.setdefault("w_yrule_value", "age")
young = queries.young(f, state.w_yrule_value, f.cutoff).merge(all_riders[["rider_bib", "age_at_start"]], on="rider_bib")
prospects = young[young["team"] != ctx.my].head(10)
rule_text = (f"age at race start under {f.cutoff}" if state.w_yrule_value == "age" else "born on or after 1 Jan 2000 (official rule)")
with ui.card("prospects", "Young prospects in other teams", sub=f"Best young riders ({rule_text}) not in our team · bar = minutes behind the GC leader · rivals' riders in their colour"):
    if prospects.empty:
        ui.note("No young rider outside our team finished the selected stages.")
    else:
        p0 = prospects.iloc[0]
        ui.takeaway(f"Best young rider outside our team: <b>{escape(p0.rider_name)}</b> ({escape(p0.team)}), {p0.age_at_start} at the start, "
                    f"{fmt.ordinal(p0.gc_rank)} in GC, {fmt.gap(p0.gap_to_gc_leader)} behind the leader.")
        st.plotly_chart(charts.h_bars([f"{n} ({a}) · {t}" for n, a, t in zip(prospects["rider_name"], prospects["age_at_start"], prospects["team"])],
                                      [g / 60 for g in prospects["gap_to_gc_leader"]],
                                      [ctx.colour(t) if ctx.is_focus(t) else "#9AA0AC" for t in prospects["team"]],
                                      texts=[f"GC {r} · {fmt.gap(g)}" for r, g in zip(prospects["gc_rank"], prospects["gap_to_gc_leader"])]),
                        width="stretch", config={"displayModeBar": False}, key="prospects_chart")
        ui.note("Age at race start in brackets. Young rider rule and cutoff: change them in the filter bar or on chapter 2. Shorter bar = closer to the yellow jersey.")

# Without E9, the E8 drill-down takes the full row
left, right = st.columns(2) if features.on("E9") else (st.container(), None)
# ---------- E8 country drill-down ----------
with left:
    code = state.w_country
    squad = all_riders[all_riders["rider_country"] == code].assign(abroad=lambda d: d["team_country"] != code) \
        .sort_values(["abroad", "rider_name"], ascending=[False, True])
    n_teams = teams_by_country.loc[teams_by_country["iso"] == code, "n"].sum()
    with ui.card("country", f"{len(squad)} rider{'s' if len(squad) != 1 else ''} · {n_teams} team{'s' if n_teams != 1 else ''} registered in {escape(names[code])}",
                 tag="E8", drill="Drill-down · country",
                 sub=f"{int(squad['abroad'].sum())} of them race for teams registered abroad (team country highlighted)"):
        st.selectbox("Choose a country", riders_by_country["iso"].tolist(), key="w_country",
                     format_func=lambda iso: f"{names[iso]} ({iso}) · {riders_by_country.set_index('iso').loc[iso, 'n']} riders")
        view = pd.DataFrame({"Rider": squad["rider_name"], "Team": squad["team"], "Team country": squad["team_country"]})
        styler = view.style.map(lambda c: "" if c == code else "color:#B4541C;font-weight:700", subset=["Team country"]) \
            .map(lambda c: f"color:{team.MY};font-weight:700" if c == ctx.my else "", subset=["Team"])
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
