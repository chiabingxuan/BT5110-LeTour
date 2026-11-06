"""About / Method: definitions, assumptions and the requirement map."""
import pandas as pd
import streamlit as st

from lib import queries, ui

ui.header(["About / Method"], "About the data and method", schema_toggle=False)

with ui.card("source", "Data source"):
    st.markdown(
        "All figures come from the **LeTour** PostgreSQL database built in Tasks 1 and 2 from the Tour de France 2025 results: "
        "184 riders in 23 teams, 21 stages and 3,602 stage results. Every number on this dashboard is computed by the SQL views "
        "and functions in `src/sql/views/`; the app only selects from them."
    )

with ui.card("story", "How the dashboard reads"):
    st.markdown(
        "The pages are a story told from a **team manager's** point of view. Choose *My team* and its *Rivals* in the sidebar: "
        "1 · Where do we stand → 2 · Our leader vs the rivals → 3 · Team strength → 4 · Where we win and lose → 5 · Scouting. "
        "Our team is drawn in a bold accent, rivals in teal and everyone else in grey; stage types keep their own colours. "
        "Each section opens with a chart and a one-line takeaway computed from the data. Tables are behind **Show data** or in the drill-downs."
    )

with ui.card("definitions", "Definitions"):
    st.markdown("""
- **Adjusted time** = finish time − time bonus + time penalty, per rider per stage. Never stored; computed in `v_stage_results`.
- **General classification (GC)**: lowest cumulative adjusted time over the selected stages. Only riders with a result on every selected stage are ranked; others show as DNF with their exit stage and reason.
- **Best team**: for each stage, the 3 fastest adjusted times per team are summed, and totals accumulate over the selected stages. A team needs 3 finishers on every selected stage.
- **Young rider**: age at race start (first stage date, 5 Jul 2025) under the cutoff, default 26. The official 2025 rule, born on or after 1 Jan 2000, is a switch on chapter 2, Our leader vs the rivals. The two rules disagree for riders born in the second half of 1999: Tobias Johannessen is 3rd under the age rule; the official podium is Lipowitz, Onley, Vauquelin.
- **Mountain proxy**: adjusted time summed over the selected mountain stages only, ranked among riders who finished all of them.
- **Inflection point (E10)**: a stage where a plotted rider's GC rank differs from the previous selected stage.
- **Ties in GC**: riders level on cumulative time are separated by the lower sum of stage placings so far, then by the better placing on the latest stage, so no two riders share a rank. After stage 4, Pogačar and Van Der Poel are level on 16:46:00; Van Der Poel is 1st on placings (54 against 92) and keeps yellow, and Pogačar takes it at stage 5.
- **Pivotal moment (E1)**: the stage with the largest swing in a rider's gap to the GC leader; ties go to the bigger rank change, then the later stage.
- **Top-10 finishes (E14)**: rank ≤ 10 in finishing order. Every rider counts, so two riders from one team on the same stage count twice; the cell drill-down shows the stages and riders behind a number.
""")

with ui.card("points", "Points and King of the Mountains are derived"):
    st.markdown(
        "The schema stores no points, so both classifications are **derived from stage finishing positions** using the scales below, "
        "and only riders who finished every selected stage are ranked. This is **not the official scoring**: the data has no intermediate sprints or categorised climbs."
    )
    points = queries.derived_scale("points")
    kom = queries.derived_scale("kom")
    st.dataframe(pd.concat([points, kom]), hide_index=True, width="stretch")
    derived_points = queries.derived_leaders("points")
    derived_kom = queries.derived_leaders("kom")
    st.markdown(
        f"**Check against the official 2025 results.** KOM: derived leader {derived_kom}; official winner Tadej Pogačar. "
        f"Points: derived leader {derived_points}; official winner Jonathan Milan. The derived Points table favours riders who place "
        "high on every terrain because sprint points are missing, so it does not reproduce the official winner."
    )

with ui.card("notes", "Known data notes"):
    st.markdown("""
- Riders' total times run about 1h02 longer than the official figure (77:02:29 vs 76:00:32 for the winner) for every rider, so all gaps are exact. Gaps match the official top 10.
- Total distance in the data is 3,302 km; the official figure is 3,338.8 km.
- On stages 1, 17 and 21, riders share group times, so rank (crossing order) sets stage placings and adjusted time sets GC.
- Exit reasons in the data are only DNS (did not start that stage) and withdrawal (abandoned during it).
- Country codes follow the race's style (SLO, GER, NED…), not strict ISO 3166-1 alpha-3. The map translates them.
""")

with ui.card("map_requirements", "Where each requirement lives"):
    st.dataframe(pd.DataFrame([
        ("a. Drill-down", "Ch 2 E1 stage grain · Ch 3 E14 team × type · Ch 4 E5 rider, E2 stage · Ch 5 E8 country"),
        ("b. Classification comparison", "Ch 2 Our leader vs the rivals › Parallel classifications"),
        ("c. Aggregate performance", "Ch 1 E10 storyline · Ch 2 E1, E7 (riders) · Ch 3 Best Team stage by stage (teams)"),
        ("d. Country participation", "Ch 5 Scouting › Riders per country, Teams per country, map"),
        ("e. Design and presentation", "Team manager storyline, team colours, one colour per stage type"),
        ("E10", "Ch 1 Where do we stand"), ("E1, E4, E7", "Ch 2 Our leader vs the rivals"), ("E14, Best team", "Ch 3 Team strength"),
        ("E5, E2, E11", "Ch 4 Where we win and lose"), ("E8", "Ch 5 Scouting"),
        ("E3 drill-down, E6, E9, E12, E13, E15", "Built but hidden; switch on in src/dashboard/lib/features.py"),
    ], columns=["Requirement", "Page and visual"]), hide_index=True, width="stretch")
