"""Time Trials: E11 catalogue of ITT stages, each result, and its effect on the GC."""
from html import escape

import pandas as pd
import streamlit as st

from lib import filters, queries, ui
from lib import format as fmt

state = st.session_state
all_stages = queries.stages()
itts = all_stages[all_stages["type"] == "individual time-trial"]
if state.get("w_itt") not in itts["stage_no"].tolist():
    state.w_itt = int(itts["stage_no"].iloc[0])

ui.header(["Time trials", f"Stage {state.w_itt}"], "Against the clock")
f = filters.bar()
selected = queries.selected_stages(f)

with ui.card("catalogue", "ITT catalogue", tag="E11",
             sub=f"{len(itts)} time trials · {itts['dist_km'].sum():.1f} km against the clock · pick one to load its result below"):
    columns = st.columns(len(itts))
    for column, row in zip(columns, itts.itertuples()):
        with column:
            border = "2px solid #2E5FA8" if row.stage_no == state.w_itt else "1px solid #E3E5EA"
            ui.html(f"""<div style="display:flex;gap:16px;align-items:center;padding:14px;border:{border};border-radius:10px">
            <span style="width:62px;height:62px;flex:none;border-radius:12px;background:#8D7FE0;color:#15171C;display:flex;align-items:center;justify-content:center;font-family:'Barlow Condensed';font-weight:700;font-size:30px">{row.stage_no}</span>
            <span style="display:flex;flex-direction:column;gap:3px"><b style="font-size:17px">{escape(row.route)}</b>
            <span class="note num">{fmt.long_date(row.date)} · {row.dist_km:.1f} km</span>
            <span class="num">Winner <b>{escape(row.winner_name)}</b> · {fmt.hms(row.winner_time)} · {row.winner_speed_kmh:.1f} km/h</span></span></div>""")
            b1, b2 = st.columns(2)
            if b1.button(f"Load stage {row.stage_no}", key=f"itt_{row.stage_no}", width="stretch",
                         type="primary" if row.stage_no == state.w_itt else "secondary"):
                state.w_itt = row.stage_no
                st.rerun()
            if b2.button("Open in Stage in focus", key=f"itt_open_{row.stage_no}", width="stretch"):
                ui.goto("stages", w_stage=row.stage_no)
    ui.note("The ITT chip in the filter bar selects the same stages across the whole dashboard.")

stage = itts[itts["stage_no"] == state.w_itt].iloc[0]
top = queries.stage_results(state.w_itt, 10)
gc = queries.gc_by_stage(f)
final = queries.gc_final(f)

left, right = st.columns([4, 3])
with left:
    with ui.card("result", f"Stage {stage.stage_no} result · top 10", sub=f"{escape(stage.route)} · speed = distance ÷ adjusted time"):
        ui.table(pd.DataFrame({
            "#": top["rank"], "Rider": top["rider_name"], "Team": top["team"], "Nat.": top["rider_country"],
            "Time": top["adjusted_time"].map(fmt.hms), "Gap": top["gap_to_winner"].map(fmt.gap), "km/h": top["speed_kmh"].map("{:.1f}".format),
        }), right=["Time", "Gap", "km/h"])
with right:
    with ui.card("effect", "What the clock did to the GC", sub=f"GC top 10 for the current filter · rank before → after stage {stage.stage_no} · time lost to the leader that day"):
        if state.w_itt not in selected["stage_no"].tolist():
            ui.note(f"Stage {stage.stage_no} is outside the current filter, so its GC effect is not computed. Widen the stage filter to include it.")
        else:
            at = gc[gc["stage_no"] == state.w_itt].set_index("rider_bib")
            leaders = final.head(10)
            rows = []
            for r in leaders.itertuples():
                g = at.loc[r.rider_bib]
                first_stage = pd.isna(g.prev_rank)
                rows.append({
                    "Rider": r.rider_name,
                    "Before": "—" if first_stage else str(int(g.prev_rank)),
                    "After": str(int(g.gc_rank)),
                    "Move": "—" if first_stage else fmt.difference(g.prev_rank - g.gc_rank),
                    "Lost to leader": fmt.gap(g.gap if first_stage else g.gap - g.prev_gap),
                })
            ui.table(pd.DataFrame(rows), right=["Before", "After", "Move", "Lost to leader"], moves=["Move"])

in_filter = [n for n in itts["stage_no"] if n in set(selected["stage_no"])]
if in_filter and not final.empty:
    with ui.card("combined", "Time lost to the GC leader in the time trials", sub="GC places 2–10 · dark = first time trial, light = second"):
        colours = ["#8D7FE0", "#C7BFF1"]
        rows, peak = [], 1
        for r in final.iloc[1:10].itertuples():
            parts = []
            for n in in_filter:
                g = gc[(gc["stage_no"] == n) & (gc["rider_bib"] == r.rider_bib)].iloc[0]
                parts.append(g.gap if pd.isna(g.prev_gap) else g.gap - g.prev_gap)
            rows.append((r.rider_name, parts))
            peak = max(peak, sum(max(0, p) for p in parts))
        html = ""
        for name, parts in rows:
            segments = "".join(f'<i style="display:block;width:{max(0, p) / peak * 100:.1f}%;background:{colours[i % 2]}"></i>' for i, p in enumerate(parts))
            html += (f'<div class="hrow num" style="grid-template-columns:minmax(0,170px) 1fr 80px"><span>{escape(name)}</span>'
                     f'<div class="bar-track" style="height:14px;display:flex;border-radius:4px">{segments}</div>'
                     f'<b style="text-align:right">{fmt.gap(sum(parts))}</b></div>')
        ui.html(html)
