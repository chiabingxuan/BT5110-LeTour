"""Stages: E2 stage in focus and E15 the long day. E11 has its own page, Time Trials."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, filters, queries, ui
from lib import format as fmt

state = st.session_state
state.setdefault("w_stage", 12)

ui.header(["Stages", f"Stage {state.w_stage}"], "Stage in focus")
f = filters.bar()
all_stages = queries.stages()
selected = queries.selected_stages(f)

with ui.card("picker", "Choose a stage", "Faded = outside the current filter"):
    ui.stage_button_css(all_stages, "pick_", selected=state.w_stage, selected_only_in=set(selected["stage_no"]))
    columns = st.columns(21, gap=None)
    for column, row in zip(columns, all_stages.itertuples()):
        if column.button(str(row.stage_no), key=f"pick_{row.stage_no}", help=row.stage_label, width="stretch"):
            state.w_stage = row.stage_no
            st.rerun()

stage = all_stages[all_stages["stage_no"] == state.w_stage].iloc[0]
ui.html(f"""
<section class="banner" aria-label="Stage banner">
  <div class="l">
    <span style="display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;letter-spacing:.06em;color:#E8D9D2"><i class="dot" style="background:{ui.TYPE_COLOURS[stage.type]}"></i>{stage.type_label.upper()} · {fmt.long_date(stage.date).upper()}</span>
    <span class="t">Stage {stage.stage_no} · {escape(stage.route)}</span>
    <span style="color:#C9CCD3">Start {stage.start_country} · Finish {stage.end_country}</span>
  </div>
  <div class="stats">
    <div><span class="eyebrow">Distance</span><span class="big">{stage.dist_km:.1f} km</span></div>
    <div><span class="eyebrow">Winner</span><b style="font-size:17px">{escape(stage.winner_name)}</b><span class="num" style="color:#C9CCD3;font-size:13px">{fmt.hms(stage.winner_time)}</span></div>
    <div><span class="eyebrow">Winner's avg speed</span><span class="big">{stage.winner_speed_kmh:.1f} km/h</span></div>
  </div>
</section>
""")

top = queries.stage_results(state.w_stage, 10)
left, right = st.columns([3, 2])
with left:
    with ui.card("top10", "Top 10 finishers", tag="E2"):
        state.setdefault("w_stage_view", "Riders")
        if not state.w_stage_view:
            state.w_stage_view = "Riders"
        st.segmented_control("View", ["Riders", "By team"], key="w_stage_view", label_visibility="collapsed")
        if state.w_stage_view == "Riders":
            view = pd.DataFrame({
                "#": top["rank"], "Rider": top["rider_name"], "Team": top["team"], "Nat.": top["rider_country"],
                "Adjusted time": top["adjusted_time"].map(fmt.hms), "Gap": top["gap_to_winner"].map(fmt.gap),
                "Bonus": top["time_bonus"].map(fmt.bonus),
            })
            event = ui.table(view, key="t_stage_top", right=["Adjusted time", "Gap", "Bonus"], select="row")
            row = ui.new_row(event, "t_stage_top")
            if row is not None:
                ui.goto("riders", w_rider=int(top.iloc[row].rider_bib))
            ui.note("Order = finishing rank; riders on the same time keep the order they crossed the line. Click a row to open the rider.")
        else:
            grouped = top.groupby("team", sort=False).agg(
                n=("rider_bib", "count"),
                riders=("rider_name", lambda s: list(s)), ranks=("rank", lambda s: list(s)),
            ).reset_index().sort_values("n", ascending=False, kind="stable")
            view = pd.DataFrame({
                "Team": grouped["team"], "In top 10": grouped["n"],
                "Riders (rank)": [", ".join(f"{n} ({r})" for n, r in zip(ns, rs)) for ns, rs in zip(grouped["riders"], grouped["ranks"])],
            })
            ui.table(view)
with right:
    with ui.card("squads", "Which squads filled the top 10", tag="E2"):
        counts = top["team"].value_counts()
        st.plotly_chart(charts.h_bars(list(counts.index), [int(v) for v in counts.values], "#2E5FA8", height=28 * len(counts) + 20),
                        width="stretch", config={"displayModeBar": False}, key="squads_chart")

ui.html('<div class="callout">Against the clock (E11) has its own page: both time trials, their results and what they did to the GC.</div>')
st.page_link(ui.PAGES["time_trials"], label="Open Time Trials →")

longest_first = selected.sort_values(["dist_km", "stage_no"], ascending=[False, True])
longest = longest_first.iloc[0]
left, right = st.columns([3, 2])
with left:
    with ui.card("longday", "The long day", tag="E15", sub="Selected stages sorted by distance · longest outlined · open any stage with the picker above"):
        labels = [f"S{r.stage_no} · {r.route}" for r in longest_first.itertuples()]
        fig = charts.h_bars(labels, list(longest_first["dist_km"]), [ui.TYPE_COLOURS[t] for t in longest_first["type"]],
                            texts=[f"{d:.1f}" for d in longest_first["dist_km"]], height=26 * len(labels) + 20)
        fig.update_traces(marker_line_width=[2.5] + [0] * (len(labels) - 1), marker_line_color="#15171C")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="longday_chart")
with right:
    with ui.card("spotlight", "Spotlight · longest stage", tag="E15"):
        ui.html(f"""<div style="display:flex;gap:12px;align-items:center"><span style="width:52px;height:52px;flex:none;border-radius:10px;background:{ui.TYPE_COLOURS[longest.type]};color:{ui.TYPE_FG[longest.type]};display:flex;align-items:center;justify-content:center;font-family:'Barlow Condensed';font-weight:700;font-size:26px">{longest.stage_no}</span>
        <span><b style="font-size:17px">{escape(longest.route)}</b><br><span class="note">{longest.type_label} · {fmt.long_date(longest.date)} · {longest.dist_km:.1f} km</span></span></div>""")
        leaders = queries.stage_results(longest.stage_no, 5)
        ui.table(pd.DataFrame({
            "#": leaders["rank"], "Rider": leaders["rider_name"], "Adjusted time": leaders["adjusted_time"].map(fmt.hms),
            "Gap": leaders["gap_to_winner"].map(fmt.gap),
        }), right=["Adjusted time", "Gap"])
        ui.note("Adjusted time includes time bonuses and penalties.")
